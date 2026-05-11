clavier matriciel 4x4 sur un Raspberry Pi 4, il faut d'abord identifier les broches et ensuite utiliser un script Python pour scanner les pressions de touches.

clavier numerique
ligne 1 : gpio 14 / 8
ligne 2 : gpio 15 /10
ligne 3 : gpio 18 / 12
ligne 4 : gpio 23 / 16

colonne 1 : gpio 24 / 18
colonne 2 : gpio 25 / 22
colonne 3 : gpio 8 / 24
colonne 4 : gpio 7 / 26

touches = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"]
]
je veux que le clavier ouvre la porte en focntion du code. ( le code peu etre modifiable dans la partie paramettre du site.)

je veux aussi avoir dans la partie teste les sotie du clavier quand j'apui sur une touche. code ca pour que ca marche sans casser le reste stp.