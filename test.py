from process import checkScore


def testScores():
    check = [
        ['HAJOS, Silvia Elvira', 'Silvia E. Hajos'],
        ['HAJOS, Silvia Elvira', 'E. Hajos Silvia'],
        ['HAJOS, Silvia Elvira', 'Silvia Hajos'],
        ['HAJOS, Silvia Elvira', 'Silvia E Hajos'],
        ['PODEROSO, Juan Jose', 'Juan José Poderoso'],
        ['PODEROSO, Juan Jose', 'Juan Josá Poderoso'],
        ['PODEROSO, Juan Jose', 'Jorge Guillermo Peralta and Juan Jose Poderoso'],
        ['VIZCAINO, Sergio Fabian', 'Sergio F. Vizcaino'],
        ['BRUNINI, Adrian', 'Adrian Brunini'],
        ['PICO, Guillermo Alfredo', 'Guillermo Pico'],
        ['PICO, Guillermo Alfredo', 'Guillermo A. do Pico'],
        ['PICO, Guillermo Alfredo', 'Guillermo A. Pico'],
        ['PICO, Guillermo Alfredo', 'Guillermo A. Do Pico'],
        ['PICO, Guillermo Alfredo', 'Guillermo Arrieta Pico'],
        ['PICO, Guillermo Alfredo', 'Guillermo A. do Pico'],
        ['PICO, Guillermo Alfredo', 'Pico Guillermo'],
        ['CONDAT, Carlos Alberto', 'Carlos A. Condat'],
        ['SALERNO, Graciela Lidia', 'Graciela L. Salerno'],
        ['SALERNO, Graciela Lidia', 'Graciela Lidia Salerno'],
        ['VILA, Alejandro Jose', 'Alejandro J. Vila'],
        ['VILA, Alejandro Jose', 'Alejandro Vila'],
        ['VILA, Alejandro Jose', 'Alejandro R. Vila'],
        ['LOMBARDI, Olimpia Iris', 'Olimpia Lombardi'],
        ['LOMBARDI, Olimpia Iris', 'Olimpia Lombardi and Martin Labarca'], # revisar
        ['CHIALVO, Abel Cesar', 'Abel C. Chialvo'],
        ['CHIALVO, Abel Cesar', 'Abel Cesar Chialvo'],
        ['CHIALVO, Abel Cesar', 'Abel Chialvo'],
        ['CHIALVO, Abel Cesar', 'C Chialvo Abel'],
        ['CUKIERMAN, Ana Lea', 'Ana Lea Cukierman'],
        ['CUKIERMAN, Ana Lea', 'Cukierman Ana Lea'],
        ['CUKIERMAN, Ana Lea', 'Cukierman Ana'],
        ['CUKIERMAN, Ana Lea', 'Ana Lea Cukierman'],
        ['APARICIO, Miriam Teresita', 'Miriam Illescas-Aparicio'],
        ['APARICIO, Miriam Teresita', 'Miriam Teresita Aparicio'],
        ['APARICIO, Miriam Teresita', 'Gladis Miriam Aparicio-Rojas'],
        ['APARICIO, Miriam Teresita', 'Miriam Aparicio'],
        ['APARICIO, Miriam Teresita', 'Gladis Miriam Aparicio Rojas'],
        ['CORACH, Daniel', 'Daniel Corach'],
        ['CORACH, Daniel', 'Corach Daniel'],
    ]

    for ch in check:
        score = checkScore(ch[0], ch[1])
        print(ch[0], ' || ', ch[1], ' || ', f'({score})')
