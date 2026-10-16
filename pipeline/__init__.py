"""
Pacote Oficial do Pipeline de Dados e Engenharia Eleitoral 2026.
Consolida os módulos de DDL/schema, download de pacotes oficiais, processamento de logs,
decodificação de BUs e compilação de cache colunar analítico Parquet.
"""

def orquestrar_pipeline(*args, **kwargs):
    from pipeline.orquestrador import orquestrar_pipeline as _orquestrar
    return _orquestrar(*args, **kwargs)

def main(*args, **kwargs):
    from pipeline.orquestrador import main as _main
    return _main(*args, **kwargs)

__all__ = [
    "orquestrar_pipeline",
    "main",
]
