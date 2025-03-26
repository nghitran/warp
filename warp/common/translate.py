import operator

try:
    import json
except ImportError:
    import simplejson as json

from warp.runtime import config, messages

def loadMessages():
    config.get("messageLoader", defaultLoader)()

def defaultLoader():
    messages.clear()
    loadMessageDir(config['warpDir'].child('messages'))
    loadMessageDir(config['siteDir'].child('messages'))

def getTranslator(language):
    lang_dict = messages.get(language, {})
    use_fallback = language != 'en_US'
    fallback_dict = messages.get('en_US', {}) if use_fallback else {}

    def get_namespace(base_dict, domain):
        if domain is None:
            return base_dict
        try:
            return reduce(operator.getitem, domain.split(":"), base_dict)
        except KeyError:
            return None

    def interpolate(text, args=None, kwargs=None):
        if args:
            try:
                return text % args
            except TypeError:
                return None
        if kwargs:
            try:
                return text % kwargs
            except KeyError:
                return None
        return text

    def t(term, *args, **kwargs):
        domain = kwargs.pop("_domain", None)
        using_fallback = False

        # Get namespace from primary language
        namespace = get_namespace(lang_dict, domain)
        if namespace is None:
            if not use_fallback:
                return u"MISSING DOMAIN: %s" % domain
            # Try fallback namespace
            namespace = get_namespace(fallback_dict, domain)
            if namespace is None:
                return u"MISSING DOMAIN: %s" % domain
            using_fallback = True

        # Get translation
        translation = namespace.get(term)
        if translation is None:
            if use_fallback and not using_fallback:
                translation = get_namespace(fallback_dict, domain).get(term, term)
            else:
                translation = term

        # Handle interpolation
        result = interpolate(translation, args, kwargs)
        if result is not None:
            return result

        # Try fallback interpolation
        if use_fallback and not using_fallback:
            fallback_translation = get_namespace(fallback_dict, domain).get(term, term)
            result = interpolate(fallback_translation, args, kwargs)
            if result is not None:
                return result

        # Return error if all interpolation attempts failed
        if args:
            return u"COULDN'T INTERPOLATE: %s // %s" % (translation, args)
        return u"COULDN'T INTERPOLATE: %s // %s" % (translation, kwargs)

    return t

# --------------------------------------- #

def loadMessageDir(messageDir):
    for language_file in messageDir.globChildren('*.json'):
        language = language_file.basename().split('.', 1)[0]

        content = json.load(language_file.open('rb'))
        lang_dict = messages.setdefault(language, {})
        _mergeDicts(content, lang_dict)

def _mergeDicts(update, target, prefix=[]):
    for k, v in update.iteritems():
        if isinstance(v, dict):
            tv = target.setdefault(k, {})
            if not isinstance(tv, dict):
                raise ValueError(
                    "%s is a dict in update but not in target"
                    % ":".join(prefix + [k]))
            _mergeDicts(v, tv, prefix + [k])
        else:
            target[k] = v
