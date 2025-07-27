class JsonTreeItem:
    def __init__(self, key, value=None, parent=None, add_to_parent=True):
        self._parent = parent
        self._key = key
        self._value = value
        self._children = []
        self._is_null = False

        if self._parent and add_to_parent:
            self._parent.add_child(self)

        self.load()

    def add_child(self, child):
        self._children.append(child)

    def insert_child(self, position, key, value):
        if position < 0 or position > len(self._children):
            return None

        item = JsonTreeItem(key, value, self, add_to_parent=False)
        self._children.insert(position, item)
        return item

    def remove_child(self, position):
        if position < 0 or position >= len(self._children):
            return
        self._children.pop(position)

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self._is_null = False
        # Clear existing children and reload
        self._children = []
        self.load()

    def set_to_null(self):
        self._value = None
        self._is_null = True
        self._children = []

    @property
    def is_null(self):
        return self._is_null

    @property
    def type(self):
        if self._is_null:
            return "null"
        if isinstance(self._value, bool):
            return "boolean"
        if isinstance(self._value, dict):
            return "dict"
        if isinstance(self._value, list):
            return "list"
        if isinstance(self._value, str):
            return "string"
        if isinstance(self._value, float):
            return "float"
        if isinstance(self._value, int):
            return "integer"
        return "unknown"

    def child(self, row):
        if 0 <= row < len(self._children):
            return self._children[row]
        return None

    def child_count(self):
        return len(self._children)

    def parent(self):
        return self._parent

    def row(self):
        if self._parent:
            return self._parent._children.index(self)
        return 0

    def load(self):
        if isinstance(self._value, dict):
            for key, value in self._value.items():
                JsonTreeItem(key, value, self)
        elif isinstance(self._value, list):
            for i, value in enumerate(self._value):
                JsonTreeItem(f"[{i}]", value, self)

    def to_python(self):
        if self.is_null:
            return None
        if self.type == "dict":
            return {child.key: child.to_python() for child in self._children}
        if self.type == "list":
            return [child.to_python() for child in self._children]
        return self.value

    def path(self, dot_notation=True) -> str | list[str]:
        path_parts = []
        current = self
        while current:
            parent: JsonTreeItem | None = current.parent()
            if parent is None:
                break
            if parent.type == "list":
                path_parts.append(str(current.row()))
            else:
                path_parts.append(current.key)

            current = current.parent()
            if current and not current.parent():  # Stop at root item's children
                break

        path_parts.reverse()
        if dot_notation:
            return ".".join(path_parts)
        return path_parts
