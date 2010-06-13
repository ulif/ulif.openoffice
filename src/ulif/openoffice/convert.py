"""
A converter for office docs.

Run this script without arguments to get help.

It needs an openoffice server running in background.

Lots of this code was taken from the official OOo documentation for
Python programmers.

  http://udk.openoffice.org/python/samples/ooextract.py

"""
import getopt, sys
from os import getcwd
from os.path import splitext

# The following wierd registratrion stuff must happen due to the fact,
# that Zope does not cope with the uno ``__import__`` replacement
# (which in fact is in a bad shape). There are different places in the
# Zope machinery, that require the original ``__import__`` function,
# because they make too much assumptions about modules, ImportErrors
# and the tracebacks they might produce. Therefore there are several
# places to blame for that mess.
#
# We disable the uno ``__import__`` function after importing uno and
# have to enable it at places, where uno-functionality is needed.
#
# Never import ``uno`` in your Zope code. If you do, use the register
# and unregister functions below immediately before and after using
# it.
#
# If you know of a decent implementation of ``__import__`` for the uno
# module, I would like to hear of it.
#
#                                                -- Uli
#
import __builtin__
_orig__import = __builtin__.__dict__['__import__']

# The default functions we use in case pyuno is recent enough not to
# fiddle around with standard import function.
def register_uno_import():
    pass
def unregister_uno_import():
    pass

try:
    # We make uno import optional to support using this package with
    # Plone and other frameworks, that blindly import everything.
    #
    # Note, that using the server components is only possible, if uno
    # is available.
    import uno
    if '_uno_import' in uno.__dict__.keys():
        # More recent pyuno versions stopped misuse of the standard
        # __import__ function.
        # We have to care for older ones, though.
        _uno__import = uno.__dict__['_uno_import']

        def register_uno_import():
            __builtin__.__dict__['__import__'] = _uno__import

        def unregister_uno_import():
            __builtin__.__dict__['__import__'] = _orig__import

    unregister_uno_import()
except ImportError:
    pass
    
def convert_file_to_html(
    url="uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext",
    # A list of internal filter names can be obtained at:
    # http://wiki.services.openoffice.org/wiki/Framework/Article/Filter/FilterList_SO_8
    filter_name="HTML (StarWriter)",
    extension="html",
    filename=None,
    data=None):
    """Convert a file to HTML.

    The function calls an OOo.org server in background to complete the task.

    The `filename` and `data` arguments represent the name of the file
    to be converted and the contents of the file.

    Returned is th path to a temporary directory, where the modified
    file and any subobjects (images, etc.) might reside.

    It is in the resposibility of the calling code to remove the directory!
    
    """
    if data is None or filename is None:
        return ''

    import tempfile
    import os
    absdir = tempfile.mkdtemp()
    absdocpath = os.path.join(absdir, filename)
    open(absdocpath, 'wb').write(data)
    status = convert_to_html(url, filter_name, extension, path=absdocpath)
    return (absdir, status)


def convert_to_html(
    url="uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext",
    # A list of internal filter names can be obtained at:
    # http://wiki.services.openoffice.org/wiki/Framework/Article/Filter/FilterList_SO_8
    filter_name="HTML (StarWriter)",
    #filter_name="XHTML Writer File",
    extension="html",
    path=None):
    """Convert the document in ``path`` to XHTML.

    Returns the HTML text. Any subobjects are placed as files in the
    document path.

    This function is not used in the ``psj`` packages, because it
    seems to suffer from race conditions when certain packages (namely
    `Products.LinguaPlone`) are used.
    """
    result = convert(url, filter_name, extension, paths=[path])
    return result

def convert_to_pdf(
    url="uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext",
    filter_name="writer_pdf_Export",
    extension="pdf",
    path=None):
    """Convert the document in ``path`` to PDF.
    
    Returns the PDF document as string. Any subobjects are placed as
    files in the document path.
    """
    return convert(url, filter_name, extension, paths=[path])

def convert(
    url="uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext",
    filter_name="Text (Encoded)",
    extension="txt",
    paths=[]):
    """Do the real conversion.
    """
    # See head of file for what's happening here.
    register_uno_import()
    from pyuno import systemPathToFileUrl, absolutize
    from com.sun.star.lang import XTypeProvider
    from com.sun.star.beans import PropertyValue
    from com.sun.star.uno import Exception as UnoException
    from com.sun.star.io import IOException, XOutputStream
    unregister_uno_import()

    # never shrinks !
    _g_typeTable = {}
    def _unohelper_getHandle(self):
        """Helper function from unohelper.py.
        """
        ret = None
        if _g_typeTable.has_key(self.__class__):
            ret = _g_typeTable[self.__class__]
        else:
            names = {}
            traverse = list(self.__class__.__bases__)
            while len(traverse) > 0:
                item = traverse.pop()
                bases = item.__bases__
                if uno.isInterface(item):
                    names[item.__pyunointerface__] = None
                elif len(bases) > 0:
                    # the "else if", because we only need the most
                    # derived interface
                    traverse = traverse + list(bases)#

            lst = names.keys()
            types = []
            for x in lst:
                t = uno.getTypeByName(x)
                types.append(t)

            ret = tuple(types) , uno.generateUuid()
            _g_typeTable[self.__class__] = ret
        return ret

    class Base(XTypeProvider):
        """Helper class from unohelper.py.
        """
        def getTypes(self):
            return _unohelper_getHandle(self)[0]
        def getImplementationId(self):
            return _unohelper_getHandle(self)[1]

    class OutputStream(Base, XOutputStream):
        def __init__(self):
            self.closed = 0
        def closeOutput(self):
            self.closed = 1
        def writeBytes(self, seq):
            sys.stdout.write(seq.value)
        def flush(self):
            pass

    ret_val = 0
    doc = None
    stdout = False
    filter_props = None
    dest_paths = []

    try:
        ctxLocal = uno.getComponentContext()
        smgrLocal = ctxLocal.ServiceManager

        resolver = smgrLocal.createInstanceWithContext(
                 "com.sun.star.bridge.UnoUrlResolver", ctxLocal)
        ctx = resolver.resolve(url)
        smgr = ctx.ServiceManager

        desktop = smgr.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)

        cwd = systemPathToFileUrl(getcwd())


        out_props = [
            PropertyValue("FilterName" , 0, filter_name , 0),
	    PropertyValue("Overwrite" , 0, True , 0),
            PropertyValue("OutputStream", 0, OutputStream(), 0),
	]

        if filter_name == "writer_pdf_Export":
            # We have to pass the `FilterData` property very
            # carefully. It must be an `uno.Any` value.
            filter_props = PropertyValue(
                "FilterData", 0, uno.Any(
                    "[]com.sun.star.beans.PropertyValue", (
                        #PropertyValue("SelectPdfVersion", 0, 1L, 0),
                        #PropertyValue("UseTaggedPDF", 0, False, 0),
                )), 0)
            out_props.append(filter_props)

        inProps = PropertyValue("Hidden" , 0 , True, 0),
        for path in paths:
            try:
                fileUrl = absolutize(cwd, systemPathToFileUrl(path))
                doc = desktop.loadComponentFromURL(
                    fileUrl , "_blank", 0, inProps)

                if not doc:
                    raise UnoException(
                        "Couldn't open stream for unknown reason", None)

		if not stdout:
                    (dest, ext) = splitext(path)
                    dest = dest + "." + extension
                    destUrl = absolutize(cwd, systemPathToFileUrl(dest))
                    doc.storeToURL(destUrl, tuple(out_props))
                    dest_paths.append(destUrl)
		else:
		    doc.storeToURL("private:stream",out_props)
            except IOException, e:
                print "Error during conversion: ", e.Message
                ret_val = 1
            except UnoException, e:
                print "UnoError during conversion: ", e.__class__, e.Message
                ret_val = 1
            if doc:
                doc.dispose()

    except UnoException, e:
        sys.stderr.write("ERROR: %s\n" % e.__class__)
        if str(e.__class__).endswith('NoConnectException'):
            sys.stderr.write("Please make sure, the OpenOffice.org server\n"
                             "is running in background.\n")
        try:
            # Many messages are in a strange encoding...
            sys.stderr.write("ERROR-MESSAGE: %s" % e.Message)
        except UnicodeEncodeError:
            pass
        ret_val = 1

    return (ret_val, dest_paths)

def usage():
    sys.stderr.write(
        "usage: ooextract.py --help | --stdout\n"+
        "       [-c <connection-string> | --connection-string=<connection-string>\n"+
        "       [--html|--pdf]\n"+
        "       [--stdout]\n"+
        "       file1 file2 ...\n"+
        "\n" +
        "Extracts plain text from documents and prints it to a file (unless --stdout is specified).\n" +
        "Requires an OpenOffice.org instance to be running. The script and the\n"+
        "running OpenOffice.org instance must be able to access the file with\n"+
        "by the same system path. [ To have a listening OpenOffice.org instance, just run:\n"+
        "openoffice \"-accept=socket,host=localhost,port=2002;urp;\" \n"
        "\n"+
        "--stdout \n" +
        "         Redirect output to stdout. Avoids writing to a file directly\n" + 
        "-c <connection-string> | --connection-string=<connection-string>\n" +
        "        The connection-string part of a uno url to where the\n" +
        "        the script should connect to in order to do the conversion.\n" +
        "        The strings defaults to socket,host=localhost,port=2002\n"
        "--html \n"
        "        Instead of the text filter, the writer html filter is used\n"
        "--pdf \n"
        "        Instead of the text filter, the pdf filter is used\n"
        )
    

def main(argv=sys.argv):
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:",
            ["help", "connection-string=" , "html", "pdf", "stdout" ])
        url = "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
        filter_name = "Text (Encoded)"
        extension  = "txt"
        for o, a in opts:
            if o in ("-h", "--help"):
                usage()
                sys.exit()
            if o in ("-c", "--connection-string"):
                url = "uno:" + a + ";urp;StarOffice.ComponentContext"
            if o == "--html":
                filter_name = "HTML (StarWriter)"
                extension  = "html"
            if o == "--pdf":
                filter_name = "writer_pdf_Export"
                extension  = "pdf"
	    if o == "--stdout":
	    	stdout = True
                
        if not len(args):
            usage()
            sys.exit()
            
        (ret_val, paths) = convert(url, filter_name, extension, args)

    except getopt.GetoptError,e:
        sys.stderr.write(str(e) + "\n")
        usage()
        ret_val = 1
    sys.exit(ret_val)



if __name__ == '__main__':
    main(argv=sys.argv)
