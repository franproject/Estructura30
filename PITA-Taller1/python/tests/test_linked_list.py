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


if __name__ == '__main__':
    unittest.main()
