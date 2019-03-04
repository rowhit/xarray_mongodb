"""Low level functions:

- loading/writing a numpy.ndarray on MongoDB
- converting between MongoDB documnents and numpy.ndarray
"""
from threading import RLock
from typing import Union, List
import numpy as np
import pymongo
from bson.objectid import ObjectId
from .errors import DocumentNotFoundError


clients = {}
clients_lock = RLock()


def mongodb_put_array(array: np.ndarray,
                      coll: pymongo.collection.Collection,
                      meta_id: ObjectId, name: str,
                      chunk: tuple, chunk_size_bytes: int) -> None:
    """Insert a single chunk into MongoDB
    """
    coll.insert_many(array_to_docs(
        array, meta_id=meta_id, name=name, chunk=chunk,
        chunk_size_bytes=chunk_size_bytes))


def mongodb_get_array(coll: pymongo.collection.Collection,
                      meta_id: ObjectId, name: str,
                      chunk: Union[tuple, None]) -> np.ndarray:
    """Insert a single chunk into MongoDB
    """
    find_key = {'meta_id': meta_id, 'name': name, 'chunk': chunk}
    docs = list(coll.find(
        find_key,
        {'dtype': 1, 'shape': 1, 'data': 1},
    ).sort('n'))
    return docs_to_array(docs, find_key)


def array_to_docs(array: np.ndarray, meta_id: ObjectId, name: str,
                  chunk: Union[tuple, None], chunk_size_bytes: int
                  ) -> List[dict]:
    """Convert a numpy array to a list of MongoDB documents ready to be
    inserted into the 'chunks' collection
    """
    buffer = array.tobytes()
    return [
        {
            'meta_id': meta_id,
            'name': name,
            'chunk': chunk,
            'n': n,
            'dtype': array.dtype.str,
            'shape': array.shape,
            'data': buffer[offset:offset + chunk_size_bytes],
        }
        for n, offset in enumerate(range(
            0, len(buffer), chunk_size_bytes))
    ]


def docs_to_array(docs: List[dict], find_key: dict) -> np.ndarray:
    """Convert a list of MongoDB documents from the 'chunks' collection
    into a numpy array.

    :param list docs:
        MongoDB documents. Must be already sorted by 'n'.
    :param dict find_key:
        tag to use when raising DocumentNotFoundError
    :raises DocumentNotFoundError:
        No documents, or one or more documents are missing
        """
    if not docs:
        raise DocumentNotFoundError(find_key)
    buffer = b''.join([doc['data'] for doc in docs])
    array = np.frombuffer(buffer, docs[0]['dtype'])
    try:
        return array.reshape(*docs[0]['shape'])
    except ValueError as e:
        # Missing some chunks
        raise DocumentNotFoundError(find_key) from e