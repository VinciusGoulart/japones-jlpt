"""Busca de DNS só por IPv4 para os hosts que o sistema chama.

Neste PC a consulta AAAA (IPv6) do DNS não responde e o glibc espera 5 s antes
de desistir — na PRIMEIRA requisição de cada processo (medido em 17/10:
getaddrinfo com AF_UNSPEC 5,04 s; com AF_INET 0,02 s). Apareceu primeiro no
Trello e de novo na voz do exercício `ouvir` (speech.platform.bing.com, 6,6 s
por frase). Restrito a estes hosts de propósito: o resto do processo segue com
a resolução normal. O conserto de verdade é `options single-request` no
resolv.conf, que é da máquina, não do repositório.
"""
import socket

HOSTS = ("trello.com", "bing.com")
_original = socket.getaddrinfo


def _getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0 and isinstance(host, str) and host.endswith(HOSTS):
        family = socket.AF_INET
    return _original(host, port, family, type, proto, flags)


socket.getaddrinfo = _getaddrinfo_ipv4
