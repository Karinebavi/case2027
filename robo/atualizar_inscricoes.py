# -*- coding: utf-8 -*-
"""
Robô que busca as inscrições novas no Wix e soma à base — sozinho, sem ninguém
abrir o sistema. Roda no GitHub (.github/workflows/robo-inscricoes.yml) de 2 em
2 horas. Faz o mesmo que o botão "Atualizar agora" (regras/atualizacao.py).

- Não usa IA e não lê documentos (a leitura dos documentos é só quando a
  Karine mandar, na tela Documental).
- O registro do GitHub é PÚBLICO: aqui só se imprime contagem, nunca nome,
  CNPJ ou e-mail.
- Também deixa o banco (Supabase) em uso, então ele não pausa.

Configuração (Secrets do GitHub): WIX_API_KEY, WIX_SITE_ID, WIX_FORM_ID,
SUPABASE_URL, SUPABASE_KEY.

Conferir sem gravar nada:  python robo/atualizar_inscricoes.py --simular
"""
import os
import sys

os.environ["CASE_ROBO"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regras import atualizacao  # noqa: E402


def main(simular=False):
    r = atualizacao.atualizar(simular=simular, origem="robô")
    if r.get("erro") in ("Wix não configurado", "banco não configurado"):
        print(f"::notice::{r['erro']} — cadastre os Secrets do GitHub (veja o topo do workflow).")
        return 0
    if not r.get("ok"):
        print(f"::error::{r.get('erro')}")
        return 1
    print(f"No Wix: {r.get('no_wix')} · ainda não estavam na base: {r.get('pendentes', 0)} · "
          f"novas: {r.get('novas', 0)} · atualizadas: {r.get('atualizadas', 0)} · base: {r.get('total_base')}")
    if simular:
        print("Simulação: nada foi gravado.")
    return 0


if __name__ == "__main__":
    sys.exit(main(simular="--simular" in sys.argv))
