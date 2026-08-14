"""A unica parte do bot que so roda no Windows.

Sem logica: traduz chamada em syscall. Toda decisao vive em codigo
testavel no macOS.

O input vai por SendInput com KEYEVENTF_SCANCODE, nao com virtual-key.
Jogos costumam ler scancode de hardware direto e ignorar evento de tecla
virtual — e a razao classica de um script funcionar no Bloco de Notas e
nao no jogo.

Exige rodar como administrador: o UIPI do Windows impede um processo de
integridade menor de enviar input a uma janela de integridade maior, e o
jogo roda elevado. Sem elevacao, o input e ignorado em silencio, sem erro.
"""

import ctypes
import time
from ctypes import wintypes

import numpy as np

LARGURA, ALTURA = 2560, 1440

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

SCANCODE_ESPACO = 0x39
SCANCODE_ESC = 0x01


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _UNIAO(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("uniao", _UNIAO)]


def _enviar(*entradas: _INPUT) -> None:
    quantidade = len(entradas)
    vetor = (_INPUT * quantidade)(*entradas)
    enviados = ctypes.windll.user32.SendInput(
        quantidade, vetor, ctypes.sizeof(_INPUT)
    )
    if enviados != quantidade:
        raise OSError(
            f"SendInput aceitou {enviados} de {quantidade} eventos. "
            "Rodando como administrador?"
        )


def _mouse(dwFlags: int, dx: int = 0, dy: int = 0) -> _INPUT:
    entrada = _INPUT(type=INPUT_MOUSE)
    entrada.uniao.mi = _MOUSEINPUT(dx, dy, 0, dwFlags, 0, None)
    return entrada


def _tecla(scancode: int, soltando: bool) -> _INPUT:
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if soltando else 0)
    entrada = _INPUT(type=INPUT_KEYBOARD)
    entrada.uniao.ki = _KEYBDINPUT(0, scancode, flags, 0, None)
    return entrada


class TelaWindows:
    def __init__(self) -> None:
        import mss  # local: nao existe no macOS

        self._mss = mss.mss()
        self._monitor = self._mss.monitors[1]

    def capturar(self) -> np.ndarray:
        quadro = np.array(self._mss.grab(self._monitor))
        return quadro[:, :, :3]  # BGRA -> BGR


# 50 ms sao ~3 quadros a 60 fps: o jogo amostra o estado do mouse ao menos uma
# vez com o botao apertado. Velocidade nao e requisito, entao a espera e
# generosa de proposito. Sao parametros, e nao constantes fechadas, porque e o
# numero a calibrar contra o jogo real — numa maquina onde ninguem depura.
PAUSA_APOS_MOVER = 0.05
SEGUNDOS_DE_CLIQUE = 0.05


class MaoWindows:
    def __init__(self, pausa_apos_mover: float = PAUSA_APOS_MOVER,
                 segundos_de_clique: float = SEGUNDOS_DE_CLIQUE) -> None:
        self._pausa_apos_mover = pausa_apos_mover
        self._segundos_de_clique = segundos_de_clique

    def clicar(self, x: int, y: int) -> None:
        # SendInput absoluto usa 0..65535 sobre a tela virtual.
        nx = x * 65535 // (LARGURA - 1)
        ny = y * 65535 // (ALTURA - 1)
        _enviar(_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, nx, ny))
        # Pressionar e soltar em lotes separados, com o botao segurado entre os
        # dois. Juntos num lote so o clique dura tempo zero: um jogo que le por
        # amostragem, e nao pela fila de mensagens, nunca ve o botao apertado.
        time.sleep(self._pausa_apos_mover)
        _enviar(_mouse(MOUSEEVENTF_LEFTDOWN))
        time.sleep(self._segundos_de_clique)
        _enviar(_mouse(MOUSEEVENTF_LEFTUP))

    def apertar_espaco(self) -> None:
        _enviar(_tecla(SCANCODE_ESPACO, False), _tecla(SCANCODE_ESPACO, True))

    def apertar_esc(self) -> None:
        _enviar(_tecla(SCANCODE_ESC, False), _tecla(SCANCODE_ESC, True))
