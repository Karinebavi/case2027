# -*- coding: utf-8 -*-
"""
Validação de CNPJ — confere os dígitos verificadores.
Não consulta a Receita; só verifica se o número é matematicamente válido.
"""


def cnpj_valido(valor) -> bool:
    digitos = "".join(c for c in str(valor) if c.isdigit())
    if len(digitos) != 14 or digitos == digitos[0] * 14:
        return False

    def digito(base):
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos = pesos[-len(base):]
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    return digito(digitos[:12]) == digitos[12] and digito(digitos[:13]) == digitos[13]
