"""
Módulo de Decodificação de Boletim de Urna Eletrônico (BU) do TSE.
Parser de alto desempenho para o formato ASN.1 DER oficial (-bu.dat).
Extrai a apuração de votos nominais e de legenda por cargo (Presidente, Governador, etc.).
"""

from typing import Dict, Any, Optional, List

def parse_der_tlv(raw: bytes) -> List[Dict[str, Any]]:
    """
    Parser recursivo ultrarrápido de DER/BER sem dependências externas pesadas.
    Decodifica Tag, Length, Value e identifica nós construídos.
    """
    items = []
    offset = 0
    raw_len = len(raw)
    
    while offset < raw_len:
        tag_byte = raw[offset]
        offset += 1
        is_constructed = bool(tag_byte & 0x20)
        tag_class = tag_byte >> 6
        tag_num = tag_byte & 0x1f
        
        if tag_num == 0x1f:
            tag_num = 0
            while offset < raw_len:
                b = raw[offset]
                offset += 1
                tag_num = (tag_num << 7) | (b & 0x7f)
                if not (b & 0x80):
                    break
                    
        if offset >= raw_len:
            break
            
        len_b = raw[offset]
        offset += 1
        if len_b & 0x80:
            n = len_b & 0x7f
            length = 0
            for _ in range(n):
                if offset < raw_len:
                    length = (length << 8) | raw[offset]
                    offset += 1
        else:
            length = len_b
            
        val_bytes = raw[offset:offset+length]
        offset += length
        
        children = parse_der_tlv(val_bytes) if is_constructed else None
        items.append({
            'tag': tag_num,
            'class': tag_class,
            'constructed': is_constructed,
            'val': val_bytes,
            'children': children
        })
    return items


class UrnaBuParser:
    """
    Parser especializado para arquivos -bu.dat do TSE.
    """

    @staticmethod
    def parse(bu_bytes: bytes) -> Dict[str, Any]:
        """
        Decodifica o envelope ASN.1 e extrai o resultado eleitoral.
        Retorna dicionário estruturado com totais e vencedores para Presidente e Governador.
        """
        resultado = {
            "presidente": None,
            "governador": None
        }
        
        try:
            tree = parse_der_tlv(bu_bytes)
            if not tree or not tree[0].get("children"):
                return resultado
            
            # 1. Localiza o OctetString interno (Tag 4 do Envelope)
            inner_raw = None
            for child in tree[0]["children"]:
                if child["tag"] == 4:
                    inner_raw = child["val"]
                    break
                    
            if not inner_raw:
                return resultado
                
            # 2. Decodifica EntidadeBoletimUrna
            inner_tree = parse_der_tlv(inner_raw)
            if not inner_tree or not inner_tree[0].get("children"):
                return resultado
                
            elements = inner_tree[0]["children"]
            if len(elements) < 9:
                return resultado
                
            # Elemento 8 é resultadosVotacaoPorEleicao (SequenceOf)
            res_votacao = elements[8]
            if not res_votacao.get("children"):
                return resultado
                
            for eleicao in res_votacao["children"]:
                if len(eleicao.get("children", [])) < 5:
                    continue
                resultados_cargos = eleicao["children"][4].get("children", [])
                
                for rc in resultados_cargos:
                    rc_children = rc.get("children", [])
                    if len(rc_children) < 3:
                        continue
                    cargos_list = rc_children[2].get("children", [])
                    
                    for cargo in cargos_list:
                        cargo_children = cargo.get("children", [])
                        if len(cargo_children) < 3:
                            continue
                        cod_cargo = int.from_bytes(cargo_children[0]["val"], "big")
                        
                        # 1 = Presidente, 3 = Governador
                        if cod_cargo not in (1, 3):
                            continue
                            
                        votos_votaveis = cargo_children[2].get("children", [])
                        votos_map = {}
                        brancos = 0
                        nulos = 0
                        total_validos = 0
                        
                        for v in votos_votaveis:
                            v_children = v.get("children", [])
                            if len(v_children) < 2:
                                continue
                            tipo_voto = int.from_bytes(v_children[0]["val"], "big")
                            qtd = int.from_bytes(v_children[1]["val"], "big")
                            
                            if tipo_voto in (1, 4): # Nominal ou Legenda
                                num_cand = None
                                if len(v_children) > 2 and v_children[2].get("children"):
                                    cand_child = v_children[2]["children"]
                                    partido = int.from_bytes(cand_child[0]["val"], "big")
                                    num_cand = int.from_bytes(cand_child[1]["val"], "big") if len(cand_child) > 1 else partido
                                if num_cand is not None:
                                    votos_map[num_cand] = votos_map.get(num_cand, 0) + qtd
                                    total_validos += qtd
                            elif tipo_voto == 2: # Branco
                                brancos += qtd
                            elif tipo_voto == 3: # Nulo
                                nulos += qtd
                                
                        # Ordena os mais votados
                        ranking = sorted(votos_map.items(), key=lambda x: x[1], reverse=True)
                        venc_num = ranking[0][0] if len(ranking) > 0 else None
                        venc_votos = ranking[0][1] if len(ranking) > 0 else 0
                        venc_pct = round((venc_votos / total_validos * 100.0), 2) if total_validos > 0 else 0.0
                        
                        seg_num = ranking[1][0] if len(ranking) > 1 else None
                        seg_votos = ranking[1][1] if len(ranking) > 1 else 0
                        seg_pct = round((seg_votos / total_validos * 100.0), 2) if total_validos > 0 else 0.0
                        
                        dados_cargo = {
                            "total_validos": total_validos,
                            "brancos": brancos,
                            "nulos": nulos,
                            "vencedor_num": venc_num,
                            "vencedor_votos": venc_votos,
                            "vencedor_pct": venc_pct,
                            "segundo_num": seg_num,
                            "segundo_votos": seg_votos,
                            "segundo_pct": seg_pct,
                            "votos": votos_map
                        }
                        
                        if cod_cargo == 1:
                            resultado["presidente"] = dados_cargo
                        elif cod_cargo == 3:
                            resultado["governador"] = dados_cargo
                            
        except Exception:
            pass
            
        return resultado
