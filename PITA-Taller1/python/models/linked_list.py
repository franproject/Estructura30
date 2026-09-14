"""Módulo de lista enlazada.

Este archivo contiene una implementación optimizada de una lista enlazada
simple con un puntero de cola para operaciones de agregado en O(1),
soportando indexación y operaciones de secuencia de estilo Python.
"""


class Node:
    """Representa un único nodo en la lista enlazada."""

    __slots__ = ("data", "next")

    def __init__(self, data, next_node=None):
        self.data = data
        self.next = next_node


class LinkedList:
    """Representa una lista enlazada simple con operaciones seguras, reutilizables y puntero de cola."""

    def __init__(self, values=None):
        """Inicializa una lista vacía o una lista a partir de un iterable."""
        self.head = None
        self.tail = None
        self.size = 0
        if values is not None:
            for value in values:
                self.insert(value)

    def __iter__(self):
        current = self.head
        while current is not None:
            yield current.data
            current = current.next

    def __len__(self):
        return self.size

    def __bool__(self):
        return not self.is_empty()

    def __repr__(self):
        return f"LinkedList({list(self)!r})"

    def __getitem__(self, index):
        """Protocolo de acceso por índice: list[i] o list[inicio:fin:paso]."""
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self.size))]

        if not isinstance(index, int):
            raise TypeError(f"Los índices de LinkedList deben ser enteros o slices, no {type(index).__name__}")

        if index < 0:
            index = self.size + index

        if index < 0 or index >= self.size:
            raise IndexError("Índice fuera de rango de LinkedList")

        if index == 0 and self.head is not None:
            return self.head.data
        if index == self.size - 1 and self.tail is not None:
            return self.tail.data

        node = self._node_at(index)
        if node is None:
            raise IndexError("Índice fuera de rango de LinkedList")
        return node.data

    def __setitem__(self, index, value):
        """Protocolo de asignación por índice: list[i] = value."""
        if not isinstance(index, int):
            raise TypeError(f"Los índices de LinkedList deben ser enteros, no {type(index).__name__}")

        if index < 0:
            index = self.size + index

        if index < 0 or index >= self.size:
            raise IndexError("Índice de asignación fuera de rango de LinkedList")

        if index == 0 and self.head is not None:
            self.head.data = value
            return
        if index == self.size - 1 and self.tail is not None:
            self.tail.data = value
            return

        node = self._node_at(index)
        if node is None:
            raise IndexError("Índice de asignación fuera de rango de LinkedList")
        node.data = value

    def __contains__(self, value):
        """Protocolo del operador 'in': value in list."""
        return self.search(value)

    def append(self, value):
        """Agrega un valor al final de la lista en tiempo O(1)."""
        self.insert(value)

    def extend(self, iterable):
        """Agrega todos los elementos del iterable a la lista."""
        for item in iterable:
            self.insert(item)

    def pop(self, index=-1):
        """Elimina y devuelve el elemento en el índice indicado (por defecto, el último)."""
        if self.size == 0:
            raise IndexError("pop desde una lista vacía")
        if index < 0:
            index = self.size + index
        if index < 0 or index >= self.size:
            raise IndexError("Índice de pop fuera de rango")
        val = self[index]
        self.remove_at(index)
        return val

    def _node_at(self, position):
        if position < 0 or position >= self.size:
            return None

        if position == 0:
            return self.head

        if position == self.size - 1 and self.tail is not None:
            return self.tail

        current = self.head
        index = 0
        while current is not None and index < position:
            current = current.next
            index += 1
        return current

    def insert(self, value, position=None):
        """Inserta un valor en la posición indicada.

        Si no se proporciona una posición (o si position >= size), el valor se agrega
        al final en tiempo O(1) usando el puntero de cola. La posición 0 inserta al
        inicio. Las posiciones negativas generan ValueError.
        """
        if position is not None and position < 0:
            raise ValueError("La posición debe ser no negativa")

        new_node = Node(value)

        # Caso 1: Lista vacía
        if self.head is None:
            self.head = new_node
            self.tail = new_node
            self.size = 1
            return

        # Caso 2: Inserción al inicio
        if position == 0:
            new_node.next = self.head
            self.head = new_node
            self.size += 1
            return

        # Caso 3: Inserción al final en O(1) usando self.tail
        if position is None or position >= self.size:
            tail = self.tail
            if tail is None:
                raise RuntimeError("Se violó la invariancia de la lista enlazada: falta la cola")
            tail.next = new_node
            self.tail = new_node
            self.size += 1
            return

        # Caso 4: Inserción intermedia
        current = self.head
        index = 0
        while current.next is not None and index < position - 1:
            current = current.next
            index += 1

        new_node.next = current.next
        current.next = new_node
        self.size += 1

    def remove(self, value):
        """Elimina la primera ocurrencia del valor dado."""
        current = self.head
        previous = None

        while current is not None:
            if current.data == value:
                if previous is None:
                    self.head = current.next
                else:
                    previous.next = current.next

                if current == self.tail:
                    self.tail = previous

                if self.head is None:
                    self.tail = None

                self.size -= 1
                return True
            previous = current
            current = current.next
        return False

    def remove_at(self, position):
        """Elimina el valor en la posición indicada."""
        if position < 0 or position >= self.size:
            return False

        if position == 0:
            self.head = self.head.next if self.head is not None else None
            if self.head is None:
                self.tail = None
            self.size -= 1
            return True

        current = self.head
        index = 0
        while current is not None and index < position - 1:
            current = current.next
            index += 1

        if current is None or current.next is None:
            return False

        target = current.next
        current.next = target.next
        if target == self.tail:
            self.tail = current

        self.size -= 1
        return True

    def get(self, position):
        """Devuelve el elemento en la posición o None si no existe."""
        node = self._node_at(position)
        if node is None:
            return None
        return node.data

    def search(self, value):
        """Devuelve True si el valor existe; de lo contrario, False."""
        current = self.head
        while current is not None:
            if current.data == value:
                return True
            current = current.next
        return False

    def find_by(self, field_name, expected_value):
        """Busca el primer elemento cuyo atributo o clave del diccionario coincide."""
        current = self.head
        while current is not None:
            item = current.data
            if isinstance(item, dict):
                if item.get(field_name) == expected_value:
                    return item
            elif hasattr(item, field_name):
                if getattr(item, field_name) == expected_value:
                    return item
            current = current.next
        return None

    def update(self, target_value, new_value):
        """Actualiza la primera coincidencia encontrada."""
        current = self.head
        while current is not None:
            if current.data == target_value:
                current.data = new_value
                return True
            current = current.next
        return False

    def update_at(self, position, new_value):
        """Actualiza el elemento en la posición indicada."""
        node = self._node_at(position)
        if node is None:
            return False
        node.data = new_value
        return True

    def update_by(self, field_name, expected_value, new_value):
        """Actualiza el primer elemento que coincida con un valor de campo."""
        current = self.head
        while current is not None:
            item = current.data
            if isinstance(item, dict):
                if item.get(field_name) == expected_value:
                    if isinstance(new_value, dict):
                        item.update(new_value)
                    else:
                        item[field_name] = new_value
                    return True
            elif hasattr(item, field_name):
                if getattr(item, field_name) == expected_value:
                    if isinstance(new_value, dict):
                        for key, value in new_value.items():
                            setattr(item, key, value)
                    else:
                        setattr(item, field_name, new_value)
                    return True
            current = current.next
        return False

    def remove_by(self, field_name, expected_value):
        """Elimina el primer elemento que coincida con un valor de campo."""
        current = self.head
        previous = None

        while current is not None:
            item = current.data
            if isinstance(item, dict):
                match = item.get(field_name) == expected_value
            elif hasattr(item, field_name):
                match = getattr(item, field_name) == expected_value
            else:
                match = False

            if match:
                if previous is None:
                    self.head = current.next
                else:
                    previous.next = current.next

                if current == self.tail:
                    self.tail = previous

                if self.head is None:
                    self.tail = None

                self.size -= 1
                return True
            previous = current
            current = current.next
        return False

    def traverse(self):
        """Devuelve una lista de nodos en su orden actual."""
        return list(self)

    def clear(self):
        """Elimina todos los elementos y restablece la lista."""
        self.head = None
        self.tail = None
        self.size = 0

    def count_elements(self):
        """Devuelve la cantidad de elementos de la lista."""
        return self.size

    def is_empty(self):
        """Devuelve True si la lista está vacía; de lo contrario, False."""
        return self.head is None
