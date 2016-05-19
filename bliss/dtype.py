"""
BLISS Primitive Data Types (PDT)

The bliss.dtype module provides definitions and functions for primitive
data types used in the construction and manipulation of OCO-3 commands
and telemetry.  Originally, this module was named bliss.types, but
types.py conflicts with Python's builtin module of the same name,
which causes all sorts of subtle import issues and conflicts.

Supported PrimitiveType names (which may be passed to bliss.dtype.get())
are listed in bliss.dtype.PrimitiveTypes.

The following code, shown via the interactive Python prompt,
demonstrates attributes and methods of the 'LSB_U16' PrimitiveType.
Several related statements are combined into a single line, forming
tuples, for succinctness:

    >>> import bliss
    >>> t = bliss.dtype.get('LSB_U16')

    >>> t.name, t.endian, t.format, t.nbits, t.nbytes
    ('LSB_U16', 'LSB', '<H', 16, 2)

    >>> t.float, t.signed
    (False, False)

    >>> t.min, t.max
    (0, 65535)

    >>> bytes = t.encode(42)
    >>> ' '.join('0x%02x' % b for b in bytes)
    '0x2a 0x00'

    >>> t.decode(bytes)
    42

    >>> t.validate(42)
    True

    # Both the array of error messages and message prefixes are optional

    >>> messages = [ ]
    >>> t.validate(65536, messages, prefix='error:')
    False

    >>> t.validate(1e6, messages, prefix='error:')
    False

    >>> print "\\n".join(messages)
    error: value '65536' out of range [0, 65535].
    error: float '1e+06' cannot be represented as an integer.

"""

"""
Authors: Ben Bornstein

Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import datetime
import dmc
import struct
import sys

import bliss

# PrimitiveTypes
#
# Lists PrimitiveType names.  Passing these names to get() will return
# the corresponding PrimitiveType.
#
# (Populated below based on information in PrimitiveTypeFormats).
#
PrimitiveTypes = None


# PrimitiveTypeMap
#
# Maps typenames to PrimitiveType.  Use bliss.dtype.get(typename).
# (Populated below based on information in PrimitiveTypeFormats).
#
PrimitiveTypeMap = {}


# PrimitiveTypeFormats
#
# Maps typenames to their corresponding Python C struct format code.
# See:
#
#   https://docs.python.org/2/library/struct.html#format-characters
#
PrimitiveTypeFormats = {
    "I8"     :  "b" ,
    "U8"     :  "B" ,
    "LSB_I16":  "<h",
    "MSB_I16":  ">h",
    "LSB_U16":  "<H",
    "MSB_U16":  ">H",
    "LSB_I32":  "<i",
    "MSB_I32":  ">i",
    "LSB_U32":  "<I",
    "MSB_U32":  ">I",
    "LSB_I64":  "<q",
    "MSB_I64":  ">q",
    "LSB_U64":  "<Q",
    "MSB_U64":  ">Q",
    "LSB_F32":  "<f",
    "MSB_F32":  ">f",
    "LSB_D64":  "<d",
    "MSB_D64":  ">d"
}

class PrimitiveType(object):
    """PrimitiveType

    A PrimitiveType contains a number of fields that provide information
    on the details of a primitive type, including: name
    (e.g. "MSB_U32"), format (Python C struct format code), endianness
    ("MSB" or "LSB"), float, signed, nbits, nbytes, min, and max.

    PrimitiveTypes can validate() specific values and encode() and
    decode() binary representations.
    """

    def __init__(self, name):
        """PrimitiveType(name) -> PrimitiveType

        Creates a new PrimitiveType based on the given typename
        (e.g. 'MSB_U16' for a big endian, 16 bit short integer).
        """
        self._name   = name
        self._format = PrimitiveTypeFormats.get(name, None)
        self._endian = None
        self._float  = False
        self._min    = None
        self._max    = None
        self._signed = False
        self._string = False

        if self.name.startswith("LSB_") or self.name.startswith("MSB_"):
            self._endian = self.name[0:3]
            self._signed = self.name[4] != "U"
            self._float  = self.name[4] == "F" or self.name[4] == "D"
            self._nbits  = int(self.name[-2:])
        elif self.name.startswith("S"):
            self._format = self.name[1:] + "s"
            self._nbits  = int(self.name[1:]) * 8
            self._string = True
        else:
            self._signed = self.name[0] != "U"
            self._nbits  = int(self.name[-1:])

        self._nbytes = self.nbits / 8

        if self.float:
            self._max = +sys.float_info.max
            self._min = -sys.float_info.max
        elif self.signed:
            self._max =  2 ** (self.nbits - 1)
            self._min = -1 *  (self.max - 1)
        elif not self.string:
            self._max = 2 ** self.nbits - 1
            self._min = 0

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.name)

    @property
    def endian(self):
        """Endianness of this PrimitiveType, either 'MSB' or 'LSB'."""
        return self._endian

    @property
    def float(self):
        """Indicates whether or not this PrimitiveType is a float or double."""
        return self._float

    @property
    def format(self):
        """Python C struct format code for this PrimitiveType."""
        return self._format

    @property
    def name(self):
        """Name of this PrimitiveType (e.g. 'I8', 'MSB_U16', 'LSB_F32', etc.)."""
        return self._name

    @property
    def nbits(self):
        """Number of bits required to represent this PrimitiveType."""
        return self._nbits

    @property
    def nbytes(self):
        """Number of bytes required to represent this PrimitiveType."""
        return self._nbytes

    @property
    def min(self):
        """Minimum value for this PrimitiveType."""
        return self._min

    @property
    def max(self):
        """Maximum value for this PrimitiveType."""
        return self._max

    @property
    def signed(self):
        """Indicates whether or not this PrimitiveType is signed or unsigned."""
        return self._signed

    @property
    def string(self):
        """Indicates whether or not this PrimitiveType is a string."""
        return self._string

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        PrimitiveType definition.
        """
        return bytearray(struct.pack(self.format, value))

    def decode(self, bytes):
        """decode(bytearray) -> value

        Decodes the given bytearray according to this PrimitiveType
        definition.
        """
        return struct.unpack(self.format, buffer(bytes))[0]

    def validate(self, value, messages=None, prefix=None):
        """validate(value[, messages[, prefix]]) -> True | False

        Validates the given value according to this PrimitiveType
        definition.  Validation error messages are appended to an optional
        messages array, each with the optional message prefix.
        """
        valid = False

        def log(msg):
            if messages is not None:
                if prefix is not None:
                    tok = msg.split()
                    msg = prefix + ' ' + tok[0].lower() + " " + " ".join(tok[1:])
                messages.append(msg)

        if self.string:
            valid = type(value) is str
        else:
            if type(value) is str:
                log("String '%s' cannot be represented as a number." % value)
            elif type(value) is not int and type(value) is not float:
                log("Value '%s' is not a primitive type." % str(value))
            elif type(value) is float and not self.float:
                log("Float '%g' cannot be represented as an integer." % value)
            else:
                if value < self.min or value > self.max:
                    args = (str(value), self.min, self.max)
                    log("Value '%s' out of range [%d, %d]." % args)
                else:
                    valid = True

        return valid

#
# Populate the PrimitiveTypeMap based on the types in
# PrimitiveTypeFormats.
#
PrimitiveTypeMap.update(
    (t, PrimitiveType(t)) for t in PrimitiveTypeFormats.keys()
)

PrimitiveTypes = sorted(PrimitiveTypeMap.keys())


class ComplexType(PrimitiveType):
    def __init__(self, pdt):
        super(ComplexType, self).__init__(pdt)


class CmdType(PrimitiveType):
    """CmdType

    This type is used to take a 2-byte opcode and return the corresponding
    CmdDefn object.
    """
    BASEPDT = "MSB_U16"

    def __init__(self):
        super(CmdType, self).__init__(self.BASEPDT)

        self._pdt = self.name
        self._name = [name for name in ComplexTypeNames.keys() if ComplexTypeNames[name] == self.__class__][0]
        self._cmddict = None

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    @property
    def cmddict(self):
        """PrimitiveType base for the ComplexType"""
        if self._cmddict is None:
            self._cmddict = bliss.cmd.getDefaultCmdDict()

        return self._cmddict

    @cmddict.setter
    def cmddict(self, value):
        """PrimitiveType base for the ComplexType"""
        self._cmddict = value

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        PrimitiveType definition.
        """
        #cmddict = self.cmddict
        opcode = self.cmddict[value].opcode
        return super(CmdType, self).encode(opcode)

    def decode(self, bytes):
        """decode(bytearray) -> value

        Decodes the given bytearray according to this ComplexType
        definition and returns a CmdDefn object
        """
        opcode = super(CmdType, self).decode(bytes)
        return self.cmddict.opcodes[opcode]


class EVRType(PrimitiveType):
    """EVRType

    This type is used to take a 4-byte error code and return the corresponding
    EVR name
    """
    BASEPDT = "MSB_U32"

    def __init__(self):
        super(EVRType, self).__init__(self.BASEPDT)

        self._pdt = self.name
        self._name = [name for name in ComplexTypeNames.keys() if ComplexTypeNames[name] == self.__class__][0]
        self._evrs = None

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    @property
    def evrs(self):
        """Getter EVRs dictionary"""
        if self._evrs is None:
            self._evrs = bliss.evr.getDefaultDict()

        return self._evrs

    @evrs.setter
    def evrs(self, value):
        """Setter for EVRs dictionary"""
        self._evrs = value

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        Complex Type definition.

        TODO better error handling?
        """
        code = [k for k, v in self._evrs.items() if v == value]

        if not code:
            bliss.log.error(str(value) + " not found as EVR. Cannot encode.")
            return None
        else:
            return super(EVRType, self).encode(code[0])

    def decode(self, bytes):
        """decode(bytearray) -> value

        Decodes the given bytearray according to this ComplexType
        definition and returns a CmdDefn object
        """
        code = super(EVRType, self).decode(bytes)
        return self.evrs[code]

class Time8Type(PrimitiveType):
    """Time8Type

    This 8-bit time type represents the fine time in the CCSDS
    secondary header. This time is calculated where the LSB of the
    octet is equal to 1/256 seconds (or 2^-8), approximately 4 msec.
    See SSP 41175-02H for more details on the CCSDS headers.
    """
    BASEPDT = "U8"

    def __init__(self):
        super(Time8Type, self).__init__(self.BASEPDT)

        self._pdt = self.name
        self._name = [name for name in ComplexTypeNames.keys() if ComplexTypeNames[name] == self.__class__][0]

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        ComplexType definition.
        """
        return super(Time8Type, self).encode(value * 256)

    def decode(self, bytes):
        """decode(bytearray) -> value

        Decodes the given bytearray according to this ComplexType
        definition.
        """
        sec = super(Time8Type, self).decode(bytes) / 256.0
        return sec


class Time32Type(PrimitiveType):
    """Time32Type

    This 4-byte time is the time represented in the CCSDS headers.
    The value represents the elapsed time since midnight 5-6 January
    1980. See SSP 41175-02H for description of this time.
    """
    BASEPDT = "MSB_U32"

    def __init__(self):
        super(Time32Type, self).__init__(self.BASEPDT)

        self._pdt = self.name
        self._name = [name for name in ComplexTypeNames.keys() if ComplexTypeNames[name] == self.__class__][0]

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        ComplexType definition.
        """
        if type(value) is not datetime.datetime:
            value = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

        return super(Time32Type, self).encode(dmc.toGPSSeconds(value))

    def decode(self, bytes):
        """decode(bytearray) -> value

        Decodes the given bytearray according to this ComplexType
        definition.
        """
        sec = super(Time32Type, self).decode(bytes)
        return bliss.dmc.toLocalTime(sec)

class Time40Type(PrimitiveType):
    """Time40Type

    This 5-byte time is a concatenation of Time32Type and Time8Type
    to more succintly represent the CCSDS Time
    """
    BASEPDT = "MSB_U32"

    def __init__(self):
        super(Time40Type, self).__init__(self.BASEPDT)

        self._pdt = self.name
        self._name = [name for name in ComplexTypeNames.keys() if ComplexTypeNames[name] == self.__class__][0]

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        ComplexType definition.
        """
        t = value.split('.')
        coarse = Time32Type().encode(t[0])
        fine = Time8Type().encode(float('0.' + t[1]))

        raw = coarse
        raw.extend(fine)
        return raw

    def decode(self, bytes):
        """decode(bytearray) -> value

        Decodes the given bytearray according to this ComplexType
        definition.
        """
        coarse = Time32Type().decode(bytes[:4])
        fine = Time8Type().decode(bytes[4:])
        fine_str = ('%f' % fine).lstrip('0')
        return '%s%s' % (coarse, fine_str)


class Time64Type(PrimitiveType):
    """Time64Type

    This 8-byte time is made up a 4-byte Time32Type with the
    remaining 4-bytes representing the subseconds. The value
    represents the elapsed time since midnight 5-6 January
    1980.
    """
    BASEPDT = "MSB_U64"

    def __init__(self):
        super(Time64Type, self).__init__(self.BASEPDT)

        self._pdt = self.name
        self._name = [name for name in ComplexTypeNames.keys() if ComplexTypeNames[name] == self.__class__][0]

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        ComplexType definition.
        """
        t = value.split('.')

        raw = Time32Type().encode(t[0])
        raw.extend( get('MSB_U32').encode( bliss.util.toNumber(t[1]) ) )
        return raw

    def decode(self, bytes):
        """decode(bytearray) -> value

        Decodes the given bytearray according to this ComplexType
        definition.
        """
        coarse = Time32Type().decode(bytes[:4])
        subsec = get('MSB_U32').decode(bytes[4:])

        return ('%s.%010d' % (coarse, subsec))

# # ComplexTypeMap
# #
# # Maps typenames to ComplexType.  Use bliss.dtype.get(typename).
#
ComplexTypeNames = {
    "CMD16": CmdType,
    "EVR16": EVRType,
    "TIME8": Time8Type,
    "TIME32": Time32Type,
    "TIME40": Time40Type,
    "TIME64": Time64Type
}

ComplexTypeMap = {}
ComplexTypeMap.update(
    (name, ComplexTypeNames.get(name)()) for name in ComplexTypeNames.keys()
)

ComplexTypes = sorted(ComplexTypeMap.keys())


#
# Populate DataTypesMap with all Primitive and Complex
# data types
DataTypeMap = {}
DataTypeMap.update(PrimitiveTypeMap)
DataTypeMap.update(ComplexTypeMap)

DataTypes = sorted(PrimitiveTypeMap.keys() + ComplexTypeMap.keys())


# # Load Command Dictionary for querying command names
# #
# # Pre-load the Command Dictionary so we only have to do it once when
# # the software is loaded, versus each time the type is instantiated
# #
# CmdDict = bliss.cmd.getDefaultCmdDict()


def getPDT(typename):
    """get(typename) -> PrimitiveType

    Returns the PrimitiveType for typename or None.
    """
    if typename not in PrimitiveTypeMap and typename.startswith("S"):
        PrimitiveTypeMap[typename] = PrimitiveType(typename)

    return PrimitiveTypeMap.get(typename, None)


def getCDT(typename):
    """getCDT(typename) -> ComplexType

    Returns the ComplexType for typename or None.
    """
    return ComplexTypeMap.get(typename, None)


def get(typename):
    """get(typename) -> PrimitiveType or ComplexType

    Returns the PrimitiveType or ComplexType for typename or None.
    """
    if typename not in DataTypeMap and typename.startswith("S"):
        PrimitiveTypeMap[typename] = PrimitiveType(typename)
        return PrimitiveTypeMap.get(typename, None)

    return DataTypeMap.get(typename, None)