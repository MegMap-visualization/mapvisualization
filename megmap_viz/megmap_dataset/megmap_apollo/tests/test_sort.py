class A:
    def __init__(self, a):
        self.a = a

    def __repr__(self):
        return f"A({self.a})"

    def __lt__(self, other):
        return self.a < other.a

    def __eq__(self, value: "A") -> bool:
        return self.a == getattr(value, "a", None)


def test_sort():
    a1 = A(1)
    a2 = A(2)
    a3 = A(3)
    a4 = A(4)
    a5 = A(5)
    a6 = A(6)
    a7 = A(7)
    test = [a4, a2, a6, a1, a3, a5, a5, a7]
    test.sort()
    assert test == [a1, a2, a3, a4, a5, a5, a6, a7]
