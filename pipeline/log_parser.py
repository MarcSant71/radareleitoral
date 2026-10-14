"""
Parser de alta performance para os logs das urnas eletrônicas (.jez / logd.dat).
Extrai a linha do tempo exata de votação, método de habilitação e indicadores de anomalia.
"""

import io
import zipfile
from datetime import datetime, time
from typing import Dict, Any, List, Optional, Tuple

# Mapeamento de fechamento oficial local equivalente a 17h Horário de Brasília
FUSO_FECHAMENTO_LOCAL = {
    "AC": time(15, 0, 0),       # UTC-5 (Acre abre 6h e fecha 15h locais = 17h Brasília)
    "AM": time(16, 0, 0),       # UTC-4 (Amazonas maior parte fecha 16h locais = 17h Brasília)
    "MT": time(16, 0, 0),       # UTC-4 (Mato Grosso fecha 16h locais)
    "MS": time(16, 0, 0),       # UTC-4 (Mato Grosso do Sul fecha 16h locais)
    "RO": time(16, 0, 0),       # UTC-4 (Rondônia fecha 16h locais)
    "RR": time(16, 0, 0),       # UTC-4 (Roraima fecha 16h locais)
}

class UrnaLogParser:
    def __init__(self, data_eleicao_str: str = "04/10/2026", uf: Optional[str] = None):
        self.data_eleicao_str = data_eleicao_str
        self.data_b = data_eleicao_str.encode("ascii")
        self.uf = uf.upper() if uf else None
        # Padrão Brasília: 17h locais. Para outros fusos, ajusta a hora limite no relógio da urna.
        self.hora_limite = FUSO_FECHAMENTO_LOCAL.get(self.uf, time(17, 0, 0)) if self.uf else time(17, 0, 0)

    def parse_from_jez(self, file_path_or_bytes) -> Dict[str, Any]:
        """Lê diretamente o .jez em memória ou arquivo sem descompactar em disco."""
        if isinstance(file_path_or_bytes, (str, bytes)):
            if isinstance(file_path_or_bytes, str):
                z = zipfile.ZipFile(file_path_or_bytes, "r")
            else:
                z = zipfile.ZipFile(io.BytesIO(file_path_or_bytes), "r")
        else:
            z = zipfile.ZipFile(file_path_or_bytes, "r")

        with z:
            if "logd.dat" not in z.namelist():
                raise ValueError("logd.dat não encontrado no pacote .jez")
            raw_logd = z.read("logd.dat")
            return self.parse_logd_bytes(raw_logd)

    def parse_logd_bytes(self, raw_logd: bytes) -> Dict[str, Any]:
        """
        Processamento ultrarrápido dos bytes de logd.dat com pré-filtros em C
        e fatiamento direto de inteiros para datas (8x mais rápido que strptime).
        """
        votos = []
        hora_encerramento = None
        current_habilitacao = "BIOMETRIA" # Default até detecção de evento manual
        inicio_habilitacao = None

        KEY_PRONTA = b"Urna pronta para receber votos"

        for raw_line in raw_logd.splitlines():
            # Filtro 1 em nível de bytes: linha deve iniciar com a data da eleição
            if not raw_line.startswith(self.data_b):
                continue

            # Filtro 2 em nível de bytes: descarta 99% das linhas irrelevantes sem decodificar string
            if not (b"eleitor" in raw_line or b"habilita" in raw_line or b"Encerramento" in raw_line 
                    or b"encerramento" in raw_line or b"pronta" in raw_line or b"dado pessoal" in raw_line):
                continue

            try:
                line = raw_line.decode("latin1", errors="replace").strip()
            except Exception:
                continue

            parts = line.split("\t")
            if len(parts) < 5:
                continue

            data_hora_str = parts[0]
            msg = parts[4]

            # Fast integer datetime slicing (elimina gargalo do strptime)
            try:
                dt = datetime(
                    int(data_hora_str[6:10]), int(data_hora_str[3:5]), int(data_hora_str[0:2]),
                    int(data_hora_str[11:13]), int(data_hora_str[14:16]), int(data_hora_str[17:19])
                )
            except Exception:
                continue

            # Autocalibra o fuso horário pelo horário de abertura da urna se não fixado por UF
            if KEY_PRONTA.decode("latin1") in msg:
                if dt.hour <= 6:
                    self.hora_limite = time(15, 0, 0) # UTC-5 (Acre / Oeste AM)
                elif dt.hour == 7:
                    self.hora_limite = time(16, 0, 0) # UTC-4 (AM, MT, MS, RO, RR)

            # Rastreia tipo de habilitação do eleitor atual
            if "Solicita" in msg and "habilita" in msg and "manual" in msg:
                current_habilitacao = "MANUAL"
            elif "Habilita" in msg and "cancelada" in msg:
                current_habilitacao = "BIOMETRIA"
                inicio_habilitacao = None
            elif "Identificador do eleitor digitado" in msg or "Foto do eleitor apresentada" in msg:
                inicio_habilitacao = dt
                current_habilitacao = "BIOMETRIA" # reinicia para o eleitor
            elif "Solicita" in msg and "dado pessoal" in msg:
                current_habilitacao = "MANUAL"

            # Evento oficial de voto computado
            if msg == "O voto do eleitor foi computado":
                duracao = None
                if inicio_habilitacao and dt >= inicio_habilitacao:
                    duracao = int((dt - inicio_habilitacao).total_seconds())

                voto_info = {
                    "datetime": dt,
                    "hora_str": dt.strftime("%H:%M:%S"),
                    "apos_17h": dt.time() >= self.hora_limite,
                    "tipo_habilitacao": current_habilitacao,
                    "duracao_segundos": duracao
                }
                votos.append(voto_info)
                
                # Reseta para o próximo eleitor
                current_habilitacao = "BIOMETRIA"
                inicio_habilitacao = None

            elif "Inicio do Encerramento" in msg or "Procedimento de encerramento confirmado" in msg:
                hora_encerramento = dt.strftime("%H:%M:%S")

        return self._calcular_metricas(votos, hora_encerramento)

    def _calcular_metricas(self, votos: List[Dict[str, Any]], hora_encerramento: Optional[str]) -> Dict[str, Any]:
        total_votos = len(votos)
        if total_votos == 0:
            return {
                "total_votos": 0,
                "primeiro_voto": None,
                "ultimo_voto": None,
                "hora_encerramento": hora_encerramento,
                "votos_antes_17h": 0,
                "votos_apos_17h": 0,
                "pct_apos_17h": 0.0,
                "maior_gap_antes_17h_min": 0.0,
                "minutos_sem_voto_ate_17h": 0.0,
                "biometria_sucesso_total": 0,
                "habilitacao_manual_total": 0,
                "biometria_sucesso_pos17h": 0,
                "habilitacao_manual_pos17h": 0,
                "pct_manual_pos17h": 0.0,
                "tempo_medio_pos17h_segundos": 0.0,
                "votos_ultrarapidos_pos17h": 0,
                "score_suspeicao": 0.0,
                "motivos_alerta": "Nenhum voto registrado no dia da eleição",
                "lista_votos": []
            }

        primeiro_voto = votos[0]["datetime"].strftime("%H:%M:%S")
        ultimo_voto = votos[-1]["datetime"].strftime("%H:%M:%S")

        votos_antes = [v for v in votos if not v["apos_17h"]]
        votos_apos = [v for v in votos if v["apos_17h"]]

        qtd_antes = len(votos_antes)
        qtd_apos = len(votos_apos)
        pct_apos = (qtd_apos / total_votos) * 100.0

        # Análise de Ociosidade antes do fechamento oficial (17h Brasília / hora_limite local)
        # 1. Maior gap entre votos na última hora antes do fechamento
        # 2. Minutos do último voto até o horário de fechamento
        hora_fechamento = self.hora_limite.hour
        hora_pre = hora_fechamento - 1
        maior_gap_pre_min = 0.0
        votos_janela_pre = [v for v in votos_antes if v["datetime"].hour == hora_pre]
        for i in range(1, len(votos_janela_pre)):
            gap_sec = (votos_janela_pre[i]["datetime"] - votos_janela_pre[i-1]["datetime"]).total_seconds()
            gap_min = gap_sec / 60.0
            if gap_min > maior_gap_pre_min:
                maior_gap_pre_min = gap_min

        minutos_ate_fechamento = 0.0
        if votos_antes:
            dt_limite = votos_antes[0]["datetime"].replace(hour=hora_fechamento, minute=0, second=0)
            diff_sec = (dt_limite - votos_antes[-1]["datetime"]).total_seconds()
            if diff_sec > 0:
                minutos_ate_fechamento = diff_sec / 60.0

        # Análise de Biometria
        manual_total = sum(1 for v in votos if v["tipo_habilitacao"] == "MANUAL")
        manual_apos = sum(1 for v in votos_apos if v["tipo_habilitacao"] == "MANUAL")
        pct_manual_apos = (manual_apos / qtd_apos * 100.0) if qtd_apos > 0 else 0.0

        # Análise de Duração / Ritmo
        duracoes_apos = [v["duracao_segundos"] for v in votos_apos if v["duracao_segundos"] is not None]
        media_duracao_apos = (sum(duracoes_apos) / len(duracoes_apos)) if duracoes_apos else 0.0
        votos_ultrarapidos = sum(1 for d in duracoes_apos if d <= 45)

        # Cálculo do Score de Suspeição e Alertas (Regras do Autor + Ampliação)
        score = 0.0
        motivos = []

        # Critério 1: Volume após 17h
        if pct_apos >= 15.0 or qtd_apos >= 30:
            score += 35.0
            motivos.append(f"Volume alto pós-17h: {qtd_apos} votos ({pct_apos:.1f}%)")
        elif pct_apos >= 10.0 or qtd_apos >= 15:
            score += 20.0
            motivos.append(f"Volume moderado pós-17h: {qtd_apos} votos ({pct_apos:.1f}%)")

        # Critério 2: Urna ociosa antes do fechamento oficial
        if minutos_ate_fechamento >= 20.0 or maior_gap_pre_min >= 20.0:
            score += 25.0
            motivos.append(f"Urna ociosa antes das 17h (gap de {max(minutos_ate_fechamento, maior_gap_pre_min):.1f} min)")

        # Critério 3: Habilitação Manual em massa após as 17h
        if qtd_apos >= 10 and pct_manual_apos >= 50.0:
            score += 25.0
            motivos.append(f"Maioria manual pós-17h: {pct_manual_apos:.1f}% sem biometria")
        elif qtd_apos >= 5 and pct_manual_apos >= 70.0:
            score += 20.0
            motivos.append(f"Alta taxa manual pós-17h: {pct_manual_apos:.1f}% sem biometria")

        # Critério 4: Ritmo excessivamente veloz após as 17h
        if qtd_apos >= 10 and media_duracao_apos > 0 and media_duracao_apos <= 45.0:
            score += 15.0
            motivos.append(f"Ritmo anômalo acelerado pós-17h: média de {media_duracao_apos:.1f}s/voto")

        score = min(100.0, score)

        return {
            "total_votos": total_votos,
            "primeiro_voto": primeiro_voto,
            "ultimo_voto": ultimo_voto,
            "hora_encerramento": hora_encerramento or ultimo_voto,
            "votos_antes_17h": qtd_antes,
            "votos_apos_17h": qtd_apos,
            "pct_apos_17h": round(pct_apos, 2),
            "maior_gap_antes_17h_min": round(maior_gap_pre_min, 1),
            "minutos_sem_voto_ate_17h": round(minutos_ate_fechamento, 1),
            "biometria_sucesso_total": total_votos - manual_total,
            "habilitacao_manual_total": manual_total,
            "biometria_sucesso_pos17h": qtd_apos - manual_apos,
            "habilitacao_manual_pos17h": manual_apos,
            "pct_manual_pos17h": round(pct_manual_apos, 2),
            "tempo_medio_pos17h_segundos": round(media_duracao_apos, 1),
            "votos_ultrarapidos_pos17h": votos_ultrarapidos,
            "score_suspeicao": round(score, 1),
            "motivos_alerta": " | ".join(motivos) if motivos else "Padrão normal",
            "lista_votos": votos
        }

if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path
    if len(sys.argv) > 1:
        sample_file = Path(sys.argv[1])
        if sample_file.exists():
            parser = UrnaLogParser()
            metricas = parser.parse_from_jez(sample_file)
            resumo = {k: v for k, v in metricas.items() if k != "lista_votos"}
            print(json.dumps(resumo, indent=2, ensure_ascii=False))
        else:
            print(f"Arquivo não encontrado: {sample_file}", file=sys.stderr)
    else:
        print("Uso: python log_parser.py <caminho_arquivo-log.jez>")
