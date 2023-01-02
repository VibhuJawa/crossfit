import functools
import types
from typing import TypeVar

import numpy as np
from dask.utils import Dispatch

from crossfit.utils import dispatch_utils


class NPBackendDispatch(Dispatch):
    def __call__(self, np_func, arg, *args, **kwargs):
        try:
            backend = self.dispatch(type(arg))
        except TypeError:
            return np_func(arg, *args, **kwargs)

        return backend(np_func, arg, *args, **kwargs)

    def get_backend(self, array_type):
        return self.dispatch(array_type)

    @property
    def supports(self):
        return dispatch_utils.supports(self)


np_backend_dispatch = NPBackendDispatch(name="np_backend_dispatch")


class NPFunctionDispatch(Dispatch):
    def __init__(self, function, name=None):
        super().__init__(name=name)
        self.function = function

    def __call__(self, arg, *args, **kwargs):
        if self.function == np.dtype:
            return self.function(arg, *args, **kwargs)

        if isinstance(arg, (np.ndarray, list)):
            return self.function(arg, *args, **kwargs)

        if self.supports(arg):
            return super().__call__(arg, *args, **kwargs)

        return np_backend_dispatch(self.function, arg, *args, **kwargs)

    def supports(self, arg) -> bool:
        try:
            self.dispatch(type(arg))

            return True
        except TypeError:
            return False


def with_dispatch(func):
    dispatch = NPFunctionDispatch(func, name=func.__name__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return dispatch(*args, **kwargs)

    wrapper.dispatch = func

    return wrapper


class NPBackend:
    def __init__(self, np_like_module):
        self.np = np_like_module

    def namespace(self):
        return np

    def __call__(self, np_func, *args, **kwargs):
        fn_name = np_func.__name__

        return getattr(self, fn_name)(*args, **kwargs)

    def __getattr__(self, name):
        if not hasattr(self.np, name):
            raise NotImplementedError(f"Function {name} not implemented for {self.np}")
        fn = getattr(self.np, name)

        return fn

    def __contains__(self, np_func):
        if isinstance(np_func, str):
            fn_name = np_func
        else:
            fn_name = np_func.__name__

        # TODO: Clean this up
        if fn_name == "dtype":
            return True

        if fn_name in CNP.no_dispatch:
            return True

        if hasattr(self, fn_name) and callable(getattr(self, fn_name)):
            return True

        if hasattr(self.np, fn_name):
            return True

        return False


class CNP(object):
    fns = {}
    no_dispatch = {"errstate", "may_share_memory", "finfo"}

    def __getattr__(self, name):
        if name.startswith("__"):
            return super().__getattr__(name)

        if not hasattr(np, name):
            raise AttributeError("Unknown numpy function")

        np_fn = getattr(np, name)
        if name in self.no_dispatch:
            return np_fn

        if name not in self.fns:
            self.fns[name] = with_dispatch(np_fn)

        return self.fns[name]


cnp = CNP()


class MonkeyPatchNumpy:
    no_dispatch = {
        "dtype",
        "errstate",
        "may_share_memory",
        "finfo",
        "ndarray",
        "isscalar",
    }

    @classmethod
    def np_patch_dict(cls, orig_np):
        to_update = {
            key: with_dispatch(val)
            for key, val in orig_np.items()
            if (
                key not in cls.no_dispatch
                and not key.startswith("_")
                and isinstance(val, types.FunctionType)
            )
        }

        return to_update

    def __enter__(self):
        self._original_numpy = np.__dict__.copy()
        patch_dict = self.np_patch_dict(self._original_numpy)
        np.__dict__.update(patch_dict)
        np.__origdict__ = self._original_numpy

    def __exit__(self, *args):
        np.__dict__.clear()
        np.__dict__.update(self._original_numpy)


FuncType = TypeVar("FuncType", bound=types.FunctionType)


def crossnp(func: FuncType) -> FuncType:
    """Make `func` work with various backends that implement the numpy-API.

    A few different scenarios are supported:
    1. Pass in a numpy function and get back the corresponding function from cnp
    2. A custom function that uses numpy functions.


    Parameters
    __________
    func: Callable
        The function to make work with various backends.


    Returns
    _______
    Callable
        The function that works with various backends.

    """

    try:
        import sklearn

        sklearn.set_config(array_api_dispatch=True)
    except ImportError:
        pass

    if isinstance(func, np.ufunc) or func.__module__ == "numpy":
        return getattr(cnp, func.__name__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with MonkeyPatchNumpy():
            return func(*args, **kwargs)

    return wrapper


__all__ = ["NPBackend", "with_dispatch", "np_backend_dispatch", "cnp", "crossnp"]