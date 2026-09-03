def gen():
    yield 1


def tet(flag):
    if flag:
        return gen()
    else:
        return 2


for i in tet(True):
    print(i)
print(tet(False))
