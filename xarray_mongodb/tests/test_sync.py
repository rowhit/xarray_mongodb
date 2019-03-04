import bson
import pytest
import xarray
from xarray_mongodb import DocumentNotFoundError
from . import xdb  # noqa: F401


ds = xarray.Dataset(
    coords={
        'x': (('x', ), [1, 2]),
        'x2': (('x', ), [3, 4]),
        'x3': (('x', ), [5, 6]),
    },
    data_vars={
        'd': (('x', 'y'), [[10, 20], [30, 40]]),
        's': 1.0,
    },
    attrs={
        'foo': 'bar'
    })
ds['d'] = ds['d'].chunk({'x': 1, 'y': 2})
ds['x3'] = ds['x3'].chunk(1)


@pytest.mark.parametrize('compute,load,chunks', [  # noqa: F811
    (False, None, {'x': None, 'x2': None,
                   'x3': ((1, 1), ), 'd': ((1, 1, ), (2, )), 's': None}),
    (False, False, {'x': None, 'x2': ((2, ), ),
                    'x3': ((1, 1), ), 'd': ((1, 1, ), (2, )), 's': ()}),
    (False, True, {'x': None, 'x2': None, 'x3': None, 'd': None, 's': None}),
    (False, ['d'], {'x': None, 'x2': ((2, ), ), 'x3': ((1, 1), ), 'd': None,
                    's': ()}),
    (True, None, {'x': None, 'x2': None, 'x3': None, 'd': None, 's': None}),
    (True, False, {'x': None, 'x2': ((2,),),
                   'x3': ((2, ),), 'd': ((2, ), (2, )), 's': ()}),
    (True, True, {'x': None, 'x2': None, 'x3': None, 'd': None, 's': None}),
    (True, ['d'], {'x': None, 'x2': ((2,),), 'x3': ((2, ),), 'd': None,
                   's': ()}),
])
def test_roundtrip(xdb, compute, load, chunks):
    if compute:
        _id, future = xdb.put(ds.compute())
        assert future is None
    else:
        _id, future = xdb.put(ds)

    assert isinstance(_id, bson.ObjectId)
    ds2 = xdb.get(_id, load=load)

    print(ds2)

    # You should be able to compute the put() after the get()
    if future is not None:
        future.compute()

    xarray.testing.assert_identical(ds, ds2)

    assert {
        k: v.chunks for k, v in ds2.variables.items()
    } == chunks


def test_meta_not_found(xdb):  # noqa: F811
    with pytest.raises(DocumentNotFoundError):
        xdb.get(bson.ObjectId('deadbeef' * 3))


def test_chunks_not_found(xdb):  # noqa: F811
    _id, _ = xdb.put(ds)
    ds2 = xdb.get(_id)
    with pytest.raises(DocumentNotFoundError):
        ds2.compute()
