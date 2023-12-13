import equinox as eqx
import jax
import jax.lax as lax
import jax.numpy as jnp
import jax.random as jr

import quax

from .helpers import tree_allclose


def test_broadcast():
    zero = quax.zero.Zero((3, 4), jnp.float32)
    true_out = quax.zero.Zero((2, 1, 3, 4), jnp.float32)
    out = quax.quaxify(jnp.broadcast_to)(zero, (2, 1, 3, 4))
    assert eqx.tree_equal(out, true_out)


def test_cast():
    zero = quax.zero.Zero((3, 4), jnp.int32)
    true_out = quax.zero.Zero((3, 4), jnp.float32)
    out1 = quax.quaxify(lambda x: x.astype(jnp.float32))(zero)
    out2 = quax.quaxify(lax.convert_element_type)(zero, jnp.float32)
    assert eqx.tree_equal(out1, true_out)
    assert eqx.tree_equal(out2, true_out)


def test_materialise():
    zero = quax.zero.Zero((3, 4), jnp.float32)
    out = zero.materialise()
    assert jnp.array_equal(out, jnp.zeros((3, 4), jnp.float32))


def test_add():
    scalar_zero = quax.zero.Zero((), jnp.float32)
    vector_zero = quax.zero.Zero((2,), jnp.bool_)
    tensor_zero = quax.zero.Zero((3, 3, 3), jnp.int32)

    for add in (lambda x, y: x + y, quax.quaxify(jnp.add)):
        assert tree_allclose(add(scalar_zero, 1), jnp.array(1.0))
        assert eqx.tree_equal(add(scalar_zero, jnp.array(1)), jnp.array(1.0))
        assert tree_allclose(add(1, scalar_zero), jnp.array(1.0))
        assert eqx.tree_equal(add(jnp.array(1), scalar_zero), jnp.array(1.0))

        assert tree_allclose(add(vector_zero, 1), jnp.array([1, 1]))
        assert eqx.tree_equal(add(vector_zero, jnp.array(1)), jnp.array([1, 1]))
        assert tree_allclose(add(1, vector_zero), jnp.array([1, 1]))
        assert eqx.tree_equal(add(jnp.array(1), vector_zero), jnp.array([1, 1]))

        assert tree_allclose(add(tensor_zero, 1), jnp.ones((3, 3, 3), jnp.int32))
        assert eqx.tree_equal(
            add(tensor_zero, jnp.array(1)), jnp.ones((3, 3, 3), jnp.int32)
        )
        assert tree_allclose(add(1, tensor_zero), jnp.ones((3, 3, 3), jnp.int32))
        assert eqx.tree_equal(
            add(jnp.array(1), tensor_zero), jnp.ones((3, 3, 3), jnp.int32)
        )


def test_mul():
    # TODO: revisit this once we support weak types.
    scalar_zero = quax.zero.Zero((), jnp.float32)
    in_vector_zero = quax.zero.Zero((2,), jnp.bool_)
    out_vector_zero = quax.zero.Zero((2,), jnp.int32)
    tensor_zero = quax.zero.Zero((3, 3, 3), jnp.int32)

    for mul in (lambda x, y: x * y, quax.quaxify(jnp.multiply)):
        assert tree_allclose(mul(scalar_zero, 1), scalar_zero)
        assert eqx.tree_equal(mul(scalar_zero, jnp.array(1)), scalar_zero)
        assert tree_allclose(mul(1, scalar_zero), scalar_zero)
        assert eqx.tree_equal(mul(jnp.array(1), scalar_zero), scalar_zero)

        assert tree_allclose(mul(in_vector_zero, 1), out_vector_zero)
        assert eqx.tree_equal(mul(in_vector_zero, jnp.array(1)), out_vector_zero)
        assert tree_allclose(mul(1, in_vector_zero), out_vector_zero)
        assert eqx.tree_equal(mul(jnp.array(1), in_vector_zero), out_vector_zero)

        assert tree_allclose(mul(tensor_zero, 1), tensor_zero)
        assert eqx.tree_equal(mul(tensor_zero, jnp.array(1)), tensor_zero)
        assert tree_allclose(mul(1, tensor_zero), tensor_zero)
        assert eqx.tree_equal(mul(jnp.array(1), tensor_zero), tensor_zero)


def test_matmul(getkey):
    for use_bias in (False, True):
        linear = eqx.nn.Linear(2, 3, key=getkey(), use_bias=use_bias)
        linear = eqx.tree_at(
            lambda x: x.weight,
            linear,
            quax.zero.Zero(linear.weight.shape, linear.weight.dtype),
        )
        out = quax.quaxify(linear)(jnp.ones(2))
        if use_bias:
            assert jnp.array_equal(out, linear.bias)
        else:
            assert eqx.tree_equal(out, quax.zero.Zero((3,), jnp.float32))


def test_dynamic_update_slice(getkey):
    zero = quax.zero.Zero((3, 4), jnp.float32)
    x = jr.normal(getkey(), (2, 3))
    out = quax.quaxify(lax.dynamic_update_slice)(zero, x, (1, 1))
    true_out = jnp.zeros((3, 4)).at[1:3, 1:4].set(x)
    assert jnp.array_equal(out, true_out)

    zero = quax.zero.Zero((3, 4), jnp.float32)
    x = quax.zero.Zero((2, 3), jnp.float32)
    out = quax.quaxify(lax.dynamic_update_slice)(zero, x, (1, 1))
    assert eqx.tree_equal(out, zero)


def test_slice(getkey):
    zero = quax.zero.Zero((5, 32, 1024), jnp.float32)
    out = quax.quaxify(lambda x: x[1:, 3:4])(zero)
    true_shape = (4, 1, 1024)
    assert eqx.tree_equal(out, quax.zero.Zero(true_shape, jnp.float32))


def test_creation():
    for maybe_jit in (jax.jit, lambda x: x):

        @maybe_jit
        @quax.quaxify
        def run(a):
            return jnp.zeros((3, 4))

        out = run(1)
        out2 = quax.quaxify(jnp.zeros)((3, 4))
        zero = quax.zero.Zero((3, 4), jnp.float32)
        assert eqx.tree_equal(out, zero)
        assert eqx.tree_equal(out2, zero)
