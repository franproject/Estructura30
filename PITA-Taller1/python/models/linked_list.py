"""Linked list module.

This file contains a reusable doubly? No, singly linked list implementation for
storing any type of value in the PITA project.
"""


class Node:
    """Represents a single node in the linked list."""

    __slots__ = ("data", "next")

    def __init__(self, data, next_node=None):
        self.data = data
        self.next = next_node


class LinkedList:
    """Represents a singly linked list with safe, reusable operations."""

    def __init__(self, values=None):
        """Initializes an empty list or a list from an iterable."""
        self.head = None
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

    def _node_at(self, position):
        if position < 0 or position >= self.size:
            return None

        current = self.head
        index = 0
        while current is not None and index < position:
            current = current.next
            index += 1
        return current

    def insert(self, value, position=None):
        """Inserts a value at the given position.

        If no position is provided, the value is appended to the end. Position 0
        inserts at the beginning; out-of-range positions are clamped to the end.
        """
        if position is None:
            position = self.size

        if position < 0:
            raise ValueError("Position must be non-negative")

        if position >= self.size:
            position = self.size

        new_node = Node(value)

        if self.head is None or position == 0:
            new_node.next = self.head
            self.head = new_node
            self.size += 1
            return

        current = self.head
        index = 0
        while current.next is not None and index < position - 1:
            current = current.next
            index += 1

        new_node.next = current.next
        current.next = new_node
        self.size += 1

    def remove(self, value):
        """Removes the first occurrence of the given value."""
        current = self.head
        previous = None

        while current is not None:
            if current.data == value:
                if previous is None:
                    self.head = current.next
                else:
                    previous.next = current.next
                self.size -= 1
                return True
            previous = current
            current = current.next
        return False

    def remove_at(self, position):
        """Removes the value at the given position."""
        if position < 0 or position >= self.size:
            return False

        if position == 0:
            self.head = self.head.next
            self.size -= 1
            return True

        current = self.head
        index = 0
        while current is not None and index < position - 1:
            current = current.next
            index += 1

        if current is None or current.next is None:
            return False

        current.next = current.next.next
        self.size -= 1
        return True

    def get(self, position):
        """Returns the element at position or None when it does not exist."""
        node = self._node_at(position)
        if node is None:
            return None
        return node.data

    def search(self, value):
        """Returns True if the value exists, otherwise False."""
        return any(current == value for current in self)

    def find_by(self, field_name, expected_value):
        """Finds the first element whose attribute or dictionary key matches."""
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
        """Updates the first matching value."""
        current = self.head
        while current is not None:
            if current.data == target_value:
                current.data = new_value
                return True
            current = current.next
        return False

    def update_at(self, position, new_value):
        """Updates the element at the given position."""
        node = self._node_at(position)
        if node is None:
            return False
        node.data = new_value
        return True

    def update_by(self, field_name, expected_value, new_value):
        """Updates the first element matching a field value."""
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
        """Removes the first element matching a field value."""
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
                self.size -= 1
                return True
            previous = current
            current = current.next
        return False

    def traverse(self):
        """Returns a list of nodes in their current order."""
        return list(self)

    def clear(self):
        """Removes all elements and resets the list."""
        self.head = None
        self.size = 0

    def count_elements(self):
        """Returns the number of elements in the list."""
        return self.size

    def is_empty(self):
        """Returns True if the list is empty, otherwise False."""
        return self.head is None
