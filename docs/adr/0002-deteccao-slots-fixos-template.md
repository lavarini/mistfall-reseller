# Detecção por slots de posição fixa + template de ícone + OCR de preço

O bot roda numa única máquina com **resolução fixa (2560x1440)**, então acoplamos a
detecção às coordenadas de pixel. Cada slot da lista (2 colunas × ~6 linhas) tem posição
fixa; dentro de cada slot identificamos o item por **template matching do ícone** (7 ícones
bem distintos → praticamente à prova de erro) e lemos apenas o número do **Preço-unitário
por OCR**. Rejeitamos ler o nome por OCR (fonte estilizada, propensa a erro) e rejeitamos
detecção independente de resolução (complexidade desnecessária para uma máquina só).

Consequência: a detecção é simples, rápida e 100% testável contra os prints existentes,
mas fica **frágil a mudanças de resolução/UI** — se a resolução mudar ou o jogo mexer no
layout do Leilão, as coordenadas e templates precisam ser recalibrados. Esse acoplamento é
deliberado, não um descuido.
