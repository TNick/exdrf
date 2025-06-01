prohibited_keys = {
    "__dict__",
    "__repr__",
    "__eq__",
    "__setitem__",
    "__getitem__",
    "__delitem__",
    "__contains__",
    "__iter__",
    "__len__",
    "__str__",
    "__bool__",
    "__int__",
    "__float__",
    "__complex__",
    "__index__",
    "__round__",
    "__ceil__",
    "__floor__",
    "__trunc__",
}


class AttrDict:
    """A dictionary that supports attribute access.

    This class is a dictionary that supports attribute access. It is
    similar to a regular dictionary, but it also supports attribute
    access.

    Example:
        ad = AttrDict(a=1, b=2)
        print(ad)
        # {a=1, b=2}

        print(ad.a)
        # 1

        ad['lop'] = 15
        print(ad)
        # {a=1, b=2, lop=15}

        print(ad.lop)
        # 15

        for k in ad:
            print(k, ad[k])
        # a 1
        # b 2
        # lop 15

        ad.a = 2222
        print(ad)
        # {a=2222, b=2, lop=15}

        del ad.a
        print(ad)
        # {b=2, lop=15}

        ad['lop'] = 15
        print(ad)
        # {b=2, lop=15}
    """

    def __init__(self, mapping_or_iterable=(), /, **kwargs):
        self.__dict__.update(mapping_or_iterable)
        self.__dict__.update(kwargs)

    def __repr__(self):
        items = (f"{k}={v!r}" for k, v in self.__dict__.items())
        return "{}({})".format(type(self).__name__, ", ".join(items))

    def __eq__(self, other):
        if isinstance(self, AttrDict) and isinstance(other, AttrDict):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __delitem__(self, key):
        if key in prohibited_keys:
            raise AttributeError(f"Cannot delete attribute {key}")
        del self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __setitem__(self, key, value):
        if key in prohibited_keys:
            raise AttributeError(f"Cannot set attribute {key}")
        self.__dict__[key] = value

    def __getitem__(self, key):
        """Get an item using square bracket notation.

        Args:
            key: The key to get the value for.

        Returns:
            The value associated with the key.

        Raises:
            KeyError: If the key is not found.
        """
        return self.__dict__[key]
