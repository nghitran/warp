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

    def t(term, *args, **kwargs):
        namespace = lang_dict

        domain = kwargs.pop("_domain", None)
        if domain is not None:
            try:
                namespace = reduce(operator.getitem, domain.split(":"), namespace)
            except KeyError:
                return u"MISSING DOMAIN: %s" % domain

        translation = namespace.get(term, term)

        if args:
            try:
                return translation % args
            except TypeError:
                return u"COULDN'T INTERPOLATE: %s // %s" % (translation, args)

        if kwargs:
            try:
                return translation % kwargs
            except KeyError:
                return u"COULDN'T INTERPOLATE: %s // %s" % (translation, kwargs)

        return translation

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
