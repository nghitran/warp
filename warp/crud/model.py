from storm.locals import *

from warp.crud import editors

class MetaCrudModel(type):
    def __init__(klass, name, bases, dct):
        if 'model' in dct:
            dct['model'].__warp_crud__ = klass


class CrudModel(object):

    __metaclass__ = MetaCrudModel

    viewRenderers = {
        Int: lambda v: str(v),
        Unicode: lambda v: v.encode("utf-8"),
        DateTime: lambda v: v.strftime("%x %H:%M"),
    }

    editRenderers = {
        Int: editors.StringEditor,
        Unicode: editors.StringEditor,
        DateTime: editors.DateEditor,
        Bool: editors.BooleanEditor,
    }

    listAttrs = {}

    listTitles = None
    crudTitles = None

    colMap = None

    def __init__(self, obj):
        self.obj = obj

        if self.colMap is None:
            self.__class__.colMap = dict(
                (v.name, k.__class__)
                for (k,v) in self.model._storm_columns.iteritems())


    def name(self):
        return self.obj.id


    def defaultView(self, colName):
        val = getattr(self.obj, colName)
        valType = self.colMap[colName]
        return self.viewRenderers[valType](val)


    def defaultEdit(self, colName):
        val = getattr(self.obj, colName)
        valType = self.colMap[colName]
        return self.editRenderers[valType](self.obj, colName)


    def renderView(self, colName):
        funcName = "render_%s" % colName
        if hasattr(self, funcName):
            return getattr(self, funcName)()
        return self.defaultView(colName)


    def _getEditor(self, colName):
        funcName = "render_edit_%s" % colName
        if hasattr(self, funcName):
            return getattr(self, funcName)()
        return self.defaultEdit(colName)


    def renderEdit(self, colName):
        return self._getEditor(colName).render()
        

    def renderListView(self, colName):
        funcName = "render_list_%s" % colName
        if hasattr(self, funcName):
            return getattr(self, funcName)()
        return self.defaultView(colName)
