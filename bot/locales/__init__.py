from locales.en import strings as en_strings
from locales.ua import strings as ua_strings

_locales = {
    "en": en_strings,
    "ua": ua_strings,
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    locale = _locales.get(lang, en_strings)
    text = locale.get(key) or en_strings.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
