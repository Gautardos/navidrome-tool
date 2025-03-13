# utils/lyrics.py
class Lyrics:
    """Classe utilitaire statique pour analyser et vérifier les propriétés des paroles."""

    @staticmethod
    def has_synced_lyrics(lyrics):
        """Vérifie si les paroles contiennent des timestamps synchronisés (format [mm:ss.xx]).

        Args:
            lyrics (str): Le texte des paroles à analyser.

        Returns:
            bool: True si les paroles sont synchronisées, False sinon.
        """
        if not lyrics:
            return False
        for line in lyrics.split('\n'):
            line = line.strip()
            if line.startswith('[') and ']' in line:
                content = line.split(']')[0][1:]  # Extrait le contenu entre [ et ]
                # Vérifie si le contenu ressemble à un timestamp [mm:ss.xx]
                try:
                    parts = content.split(':')
                    if len(parts) == 2:  # Format [mm:ss]
                        minutes, seconds = map(float, parts)
                        if 0 <= minutes < 60 and 0 <= seconds < 60:
                            return True
                    elif len(parts) == 3:  # Format [mm:ss.xx]
                        minutes, seconds = map(float, parts[:2])
                        if 0 <= minutes < 60 and 0 <= seconds < 60:
                            return True
                except ValueError:
                    continue  # Ignorer les lignes non conformes
        return False

    @staticmethod
    def has_any_lyrics(lyrics):
        """Vérifie si des paroles (synchronisées ou non) sont présentes.

        Args:
            lyrics (str): Le texte des paroles à analyser.

        Returns:
            bool: True si des paroles sont présentes, False sinon.
        """
        return bool(lyrics and lyrics.strip())

    @staticmethod
    def get_lyrics_type(lyrics):
        """Détermine le type de paroles : synchronisées, non-synchronisées ou absentes.

        Args:
            lyrics (str): Le texte des paroles à analyser.

        Returns:
            str: 'sync' si synchronisées, 'unsync' si non-synchronisées mais présentes, None si absentes.
        """
        if not lyrics or not lyrics.strip():
            return None
        return 'sync' if Lyrics.has_synced_lyrics(lyrics) else 'unsync'

    @staticmethod
    def count_lines(lyrics):
        """Compte le nombre de lignes dans les paroles.

        Args:
            lyrics (str): Le texte des paroles à analyser.

        Returns:
            int: Nombre de lignes (0 si aucune parole).
        """
        return len(lyrics.split('\n')) if lyrics else 0

    @staticmethod
    def has_timestamp_format(lyrics, format_pattern="[mm:ss]"):
        """Vérifie si les paroles contiennent des timestamps dans un format spécifique.

        Args:
            lyrics (str): Le texte des paroles à analyser.
            format_pattern (str): Modèle de timestamp à vérifier (par défaut "[mm:ss]").

        Returns:
            bool: True si le format est détecté, False sinon.
        """
        if not lyrics:
            return False
        for line in lyrics.split('\n'):
            line = line.strip()
            if line.startswith('[') and ']' in line:
                content = line.split(']')[0][1:]
                if format_pattern == "[mm:ss]":
                    parts = content.split(':')
                    if len(parts) == 2:
                        try:
                            minutes, seconds = map(float, parts)
                            return 0 <= minutes < 60 and 0 <= seconds < 60
                        except ValueError:
                            continue
                elif format_pattern == "[mm:ss.xx]":
                    parts = content.split(':')
                    if len(parts) == 3:
                        try:
                            minutes, seconds = map(float, parts[:2])
                            return 0 <= minutes < 60 and 0 <= seconds < 60
                        except ValueError:
                            continue
        return False

    @staticmethod
    def analyze_lyrics(lyrics):
        """Analyse les paroles et retourne un dictionnaire avec plusieurs propriétés.

        Args:
            lyrics (str): Le texte des paroles à analyser.

        Returns:
            dict: Dictionnaire contenant les résultats des vérifications (has_synced, has_any, type, line_count).
        """
        return {
            "has_synced": Lyrics.has_synced_lyrics(lyrics),
            "has_any": Lyrics.has_any_lyrics(lyrics),
            "type": Lyrics.get_lyrics_type(lyrics),
            "line_count": Lyrics.count_lines(lyrics)
        }
