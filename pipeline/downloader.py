"""
Módulo de Download de Dados Eleitorais do TSE.
Implementa duas estratégias de alta eficiência:
1. Range Requests HTTP em ZIPs remotos da CDN (método do esteleicao): baixa apenas o índice
   e os logs necessários sem baixar os 6+ GB do pacote da UF.
2. API REST do Portal de Resultados: para consultas pontuais de seções específicas em tempo real.
"""

import io
import struct
import urllib.request
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Generator

CDN_BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/arqurnatot"
RESULTADOS_BASE_URL = "https://resultados.tse.jus.br/oficial"

class RemoteZipRangeReader:
    """
    Leitor remoto de arquivos ZIP/ZIP64 utilizando requisições HTTP Range parciais.
    Permite inspecionar e extrair arquivos individuais sem baixar o ZIP completo.
    """
    def __init__(self, url: str):
        self.url = url
        self.total_size = 0
        self.entries: Dict[str, Dict] = {}

    def connect(self) -> None:
        """Obtém o tamanho do arquivo e carrega o índice central (Central Directory)."""
        req = urllib.request.Request(self.url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        with urllib.request.urlopen(req) as resp:
            self.total_size = int(resp.headers['Content-Length'])

        # Lê os últimos 65KB para localizar o EOCD / Zip64 Locator
        tail_size = 65536
        tail_start = max(0, self.total_size - tail_size)
        tail_data = self._read_range(tail_start, self.total_size - 1)

        zip64_loc_pos = tail_data.rfind(b'PK\x06\x07')
        if zip64_loc_pos != -1:
            loc_bytes = tail_data[zip64_loc_pos:zip64_loc_pos + 20]
            sig, disk_num, zip64_eocd_offset, total_disks = struct.unpack('<4sIQI', loc_bytes)
            
            # Lê o cabeçalho Zip64 EOCD
            eocd64 = self._read_range(zip64_eocd_offset, zip64_eocd_offset + 56)
            sig64, size64, ver, ver_need, d_num, d_cd, entries_disk, total_entries, cd_size, cd_offset = struct.unpack('<4sQHHIIQQQQ', eocd64[:56])
        else:
            eocd_pos = tail_data.rfind(b'PK\x05\x06')
            if eocd_pos == -1:
                raise ValueError("Estrutura ZIP não reconhecida no arquivo remoto")
            eocd_bytes = tail_data[eocd_pos:eocd_pos + 22]
            sig, d_num, d_cd, entries_disk, total_entries, cd_size, cd_offset, comment_len = struct.unpack('<4sHHHHIIH', eocd_bytes)

        # Baixa apenas o Central Directory
        cd_data = self._read_range(cd_offset, cd_offset + cd_size - 1)
        self._parse_central_directory(cd_data)

    def _read_range(self, start: int, end: int) -> bytes:
        req = urllib.request.Request(self.url)
        req.add_header('Range', f'bytes={start}-{end}')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        with urllib.request.urlopen(req) as resp:
            return resp.read()

    def _parse_central_directory(self, data: bytes) -> None:
        pos = 0
        data_len = len(data)
        while pos + 46 <= data_len:
            if data[pos:pos+4] != b'PK\x01\x02':
                break
            
            header = data[pos:pos+46]
            (sig, ver_made, ver_need, flags, method, mod_time, mod_date, crc32,
             comp_size, uncomp_size, name_len, extra_len, comment_len,
             disk_num, int_attr, ext_attr, local_hdr_offset) = struct.unpack('<4sHHHHHHIIIHHHHHII', header)
            
            name_bytes = data[pos+46:pos+46+name_len]
            filename = name_bytes.decode('latin1', errors='replace')
            extra_data = data[pos+46+name_len:pos+46+name_len+extra_len]

            # Processa extensão Zip64 se campos excederem 32-bit
            if comp_size == 0xFFFFFFFF or uncomp_size == 0xFFFFFFFF or local_hdr_offset == 0xFFFFFFFF:
                xpos = 0
                while xpos + 4 <= len(extra_data):
                    header_id, block_size = struct.unpack('<HH', extra_data[xpos:xpos+4])
                    xpos += 4
                    if header_id == 0x0001:
                        if uncomp_size == 0xFFFFFFFF and xpos + 8 <= len(extra_data):
                            uncomp_size = struct.unpack('<Q', extra_data[xpos:xpos+8])[0]
                            xpos += 8
                        if comp_size == 0xFFFFFFFF and xpos + 8 <= len(extra_data):
                            comp_size = struct.unpack('<Q', extra_data[xpos:xpos+8])[0]
                            xpos += 8
                        if local_hdr_offset == 0xFFFFFFFF and xpos + 8 <= len(extra_data):
                            local_hdr_offset = struct.unpack('<Q', extra_data[xpos:xpos+8])[0]
                            xpos += 8
                        break
                    else:
                        xpos += block_size

            self.entries[filename] = {
                "filename": filename,
                "comp_size": comp_size,
                "uncomp_size": uncomp_size,
                "method": method,
                "local_offset": local_hdr_offset,
                "crc32": crc32
            }
            pos += 46 + name_len + extra_len + comment_len

    def read_file(self, filename: str) -> bytes:
        """Baixa e descompacta um arquivo específico a partir de seu offset remoto."""
        if filename not in self.entries:
            raise KeyError(f"Arquivo {filename} não encontrado no índice remoto")
        
        entry = self.entries[filename]
        offset = entry["local_offset"]
        comp_size = entry["comp_size"]

        # Lê cabeçalho local (30 bytes fixos + tamanhos variáveis)
        header_bytes = self._read_range(offset, offset + 30)
        sig, ver, flags, method, mtime, mdate, crc, c_size, u_size, fname_len, extra_len = struct.unpack('<4sHHHHHIIIHH', header_bytes[:30])
        
        data_start = offset + 30 + fname_len + extra_len
        raw_compressed = self._read_range(data_start, data_start + comp_size - 1)

        if entry["method"] == 0:  # STORED (sem compressão)
            return raw_compressed
        elif entry["method"] == 8:  # DEFLATE
            import zlib
            return zlib.decompress(raw_compressed, -15)
        else:
            raise NotImplementedError(f"Método de compressão {entry['method']} não suportado")


def download_secao_por_api(ciclo: str, pleito: str, uf: str, municipio: str, zona: str, secao: str) -> Dict[str, bytes]:
    """
    Baixa os arquivos de urna de uma seção específica via API de Resultados do TSE.
    Retorna dicionário contendo os bytes do BU e do Log.
    """
    uf = uf.lower()
    mu_pad = str(municipio).zfill(5)
    zn_pad = str(zona).zfill(4)
    se_pad = str(secao).zfill(4)
    pleito_pad = str(pleito).zfill(6)

    # 1. Obtém metadados auxiliares com hashes
    aux_url = f"{RESULTADOS_BASE_URL}/{ciclo}/arquivo-urna/{pleito}/dados/{uf}/{mu_pad}/{zn_pad}/{se_pad}/p{pleito_pad}-{uf}-m{mu_pad}-z{zn_pad}-s{se_pad}-aux.json"
    
    req = urllib.request.Request(aux_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        meta = json.loads(resp.read().decode('utf-8'))

    hashes = meta.get("hashes", [])
    if not hashes:
        raise ValueError(f"Nenhum arquivo disponível para a seção {se_pad}")

    hash_principal = hashes[0]["hash"]
    arquivos = hashes[0].get("arq", [])

    resultado = {"meta": meta, "arquivos": {}}
    for arq in arquivos:
        nome_arq = arq["nm"]
        tipo = arq["tp"]
        file_url = f"{RESULTADOS_BASE_URL}/{ciclo}/arquivo-urna/{pleito}/dados/{uf}/{mu_pad}/{zn_pad}/{se_pad}/{hash_principal}/{nome_arq}"
        req_file = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_file) as r_file:
            resultado["arquivos"][tipo] = r_file.read()

    return resultado

if __name__ == "__main__":
    print("Testando conexão ao ZIP da Bahia na CDN...")
    reader = RemoteZipRangeReader(f"{CDN_BASE_URL}/bu_imgbu_logjez_rdv_vscmr_2026_1t_BA.zip")
    reader.connect()
    logs = [f for f in reader.entries.keys() if f.endswith("-log.jez")]
    print(f"Total de arquivos indexados no ZIP da Bahia: {len(reader.entries)}")
    print(f"Total de logs de urna disponíveis: {len(logs)}")
    if logs:
        print("Exemplo de log encontrado:", logs[0])
