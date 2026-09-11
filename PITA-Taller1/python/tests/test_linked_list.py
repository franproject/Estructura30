import time
import unittest

from models.linked_list import LinkedList


class LinkedListTests(unittest.TestCase):
    def test_insert_and_count_and_empty(self):
        values = LinkedList()
        self.assertTrue(values.is_empty())
        self.assertEqual(len(values), 0)

        values.insert(10)
        values.insert(20)
        values.insert(30, position=1)

        self.assertFalse(values.is_empty())
        self.assertEqual(values.count_elements(), 3)
        self.assertEqual(len(values), 3)
        self.assertEqual(list(values), [10, 30, 20])

    def test_get_and_update_and_search(self):
        values = LinkedList([10, 20, 30])
        self.assertEqual(values.get(0), 10)
        self.assertEqual(values.get(2), 30)
        self.assertIsNone(values.get(99))
        self.assertTrue(values.search(20))
        self.assertTrue(values.update(20, 25))
        self.assertEqual(values.get(1), 25)

    def test_remove_and_clear_and_edge_cases(self):
        values = LinkedList([1, 2, 3, 2])
        self.assertTrue(values.remove(2))
        self.assertEqual(list(values), [1, 3, 2])

        self.assertTrue(values.remove_at(0))
        self.assertEqual(list(values), [3, 2])

        values.clear()
        self.assertTrue(values.is_empty())
        self.assertEqual(values.count_elements(), 0)
        self.assertFalse(values.remove(9))

    def test_find_update_remove_by_field(self):
        class Item:
            def __init__(self, student_id, name):
                self.student_id = student_id
                self.name = name

        items = LinkedList()
        items.insert(Item(1, 'Ana'))
        items.insert(Item(2, 'Luis'))

        found = items.find_by('student_id', 2)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, 'Luis')

        self.assertTrue(items.update_by('student_id', 1, {'name': 'Ana Maria'}))
        self.assertEqual(items.get(0).name, 'Ana Maria')

        self.assertTrue(items.remove_by('student_id', 2))
        self.assertEqual(items.count_elements(), 1)

    def test_tail_pointer_consistency_on_insert(self):
        """Verifica que el puntero tail se mantenga sincronizado en inserciones."""
        ll = LinkedList()
        self.assertIsNone(ll.head)
        self.assertIsNone(ll.tail)

        # Inserción en lista vacía
        ll.insert(100)
        self.assertIsNotNone(ll.head)
        self.assertIsNotNone(ll.tail)
        self.assertEqual(ll.head.data, 100)
        self.assertEqual(ll.tail.data, 100)

        # Inserción al final
        ll.insert(200)
        self.assertEqual(ll.head.data, 100)
        self.assertEqual(ll.tail.data, 200)

        # Inserción al inicio (no altera tail)
        ll.insert(50, position=0)
        self.assertEqual(ll.head.data, 50)
        self.assertEqual(ll.tail.data, 200)

        # Inserción intermedia (no altera tail)
        ll.insert(75, position=2)
        self.assertEqual(ll.tail.data, 200)
        self.assertEqual(list(ll), [50, 100, 75, 200])

        # Inserción al final explícita (position >= size)
        ll.insert(300, position=len(ll))
        self.assertEqual(ll.tail.data, 300)
        self.assertEqual(list(ll), [50, 100, 75, 200, 300])

    def test_tail_pointer_consistency_on_remove(self):
        """Verifica que tail se actualice adecuadamente al remover elementos."""
        ll = LinkedList([1, 2, 3])
        self.assertEqual(ll.tail.data, 3)

        # Remover el último elemento
        self.assertTrue(ll.remove(3))
        self.assertEqual(ll.tail.data, 2)
        self.assertIsNone(ll.tail.next)

        # Remover con remove_at del último
        self.assertTrue(ll.remove_at(1))
        self.assertEqual(ll.tail.data, 1)
        self.assertEqual(ll.head.data, 1)

        # Remover el único elemento restante
        self.assertTrue(ll.remove_at(0))
        self.assertIsNone(ll.head)
        self.assertIsNone(ll.tail)
        self.assertEqual(len(ll), 0)

    def test_tail_pointer_with_remove_by(self):
        """Verifica que remove_by actualice el puntero tail si se remueve el nodo final."""
        class Obj:
            def __init__(self, key, val):
                self.key = key
                self.val = val

        ll = LinkedList([Obj(1, "A"), Obj(2, "B"), Obj(3, "C")])
        self.assertEqual(ll.tail.data.key, 3)

        self.assertTrue(ll.remove_by("key", 3))
        self.assertEqual(ll.tail.data.key, 2)
        self.assertIsNone(ll.tail.next)

    def test_getitem_positive_and_negative_indices(self):
        """Verifica la sintaxis lista[i] con índices positivos y negativos."""
        ll = LinkedList(["alpha", "beta", "gamma", "delta"])

        # Índices positivos
        self.assertEqual(ll[0], "alpha")
        self.assertEqual(ll[1], "beta")
        self.assertEqual(ll[2], "gamma")
        self.assertEqual(ll[3], "delta")

        # Índices negativos
        self.assertEqual(ll[-1], "delta")
        self.assertEqual(ll[-2], "gamma")
        self.assertEqual(ll[-4], "alpha")

        # Excepciones de índice fuera de rango
        with self.assertRaises(IndexError):
            _ = ll[4]
        with self.assertRaises(IndexError):
            _ = ll[-5]
        with self.assertRaises(TypeError):
            _ = ll["invalid"]

    def test_getitem_slice_support(self):
        """Verifica la sintaxis lista[start:stop]."""
        ll = LinkedList([10, 20, 30, 40, 50])
        self.assertEqual(ll[1:4], [20, 30, 40])
        self.assertEqual(ll[:2], [10, 20])
        self.assertEqual(ll[3:], [40, 50])

    def test_setitem_positive_and_negative_indices(self):
        """Verifica la sintaxis lista[i] = value."""
        ll = LinkedList([1, 2, 3])

        ll[0] = 10
        self.assertEqual(ll[0], 10)
        self.assertEqual(ll.head.data, 10)

        ll[-1] = 30
        self.assertEqual(ll[-1], 30)
        self.assertEqual(ll.tail.data, 30)

        ll[1] = 20
        self.assertEqual(list(ll), [10, 20, 30])

        with self.assertRaises(IndexError):
            ll[5] = 99
        with self.assertRaises(IndexError):
            ll[-4] = 99

    def test_append_extend_pop_and_contains(self):
        """Verifica los métodos de compatibilidad tipo lista."""
        ll = LinkedList()

        # append
        ll.append(10)
        ll.append(20)
        self.assertEqual(list(ll), [10, 20])
        self.assertEqual(ll.tail.data, 20)

        # extend
        ll.extend([30, 40])
        self.assertEqual(list(ll), [10, 20, 30, 40])
        self.assertEqual(ll.tail.data, 40)

        # in operator
        self.assertTrue(30 in ll)
        self.assertFalse(99 in ll)

        # pop
        last = ll.pop()
        self.assertEqual(last, 40)
        self.assertEqual(ll.tail.data, 30)
        self.assertEqual(len(ll), 3)

        first = ll.pop(0)
        self.assertEqual(first, 10)
        self.assertEqual(ll.head.data, 20)
        self.assertEqual(len(ll), 2)

    def test_o1_tail_append_performance(self):
        """Verifica que insertar 5,000 elementos sea O(1) por inserción y O(N) total (< 0.1s)."""
        ll = LinkedList()
        t0 = time.perf_counter()
        for i in range(5000):
            ll.insert(i)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(ll), 5000)
        self.assertEqual(ll.tail.data, 4999)
        self.assertEqual(ll[0], 0)
        self.assertEqual(ll[-1], 4999)
        # Antes de tail tardaba ~1.12s, con tail debe tardar < 0.05s
        self.assertLess(elapsed, 0.15, f"La inserción de 5,000 elementos tardó {elapsed:.4f}s (esperado < 0.15s)")


if __name__ == '__main__':
    unittest.main()
