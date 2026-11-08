import pytest


def test_single(benchmark):
    runs = []
    benchmark.pedantic(runs.append, args=[123])
    assert runs == [123]


def test_setup(benchmark):
    runs = []

    def stuff(foo, bar=123):
        runs.append((foo, bar))

    def setup():
        return [1], {'bar': 2}

    benchmark.pedantic(stuff, setup=setup)
    assert runs == [(1, 2)]


def test_teardown(benchmark):
    runs = []

    def stuff(foo, bar=1234):
        runs.append((foo, bar))

    def teardown(foo, bar=1234):
        assert foo == 1
        assert bar == 2
        runs.append('teardown')

    benchmark.pedantic(stuff, args=[1], kwargs={'bar': 2}, teardown=teardown)
    assert runs == [(1, 2), 'teardown']


@pytest.mark.benchmark(cprofile=True)
def test_setup_cprofile(benchmark):
    runs = []

    def stuff(foo, bar=123):
        runs.append((foo, bar))

    def setup():
        return [1], {'bar': 2}

    benchmark.pedantic(stuff, setup=setup)
    assert runs == [(1, 2), (1, 2)]


@pytest.mark.benchmark(cprofile=True)
def test_teardown_cprofile(benchmark):
    runs = []

    def stuff():
        runs.append('stuff')

    def teardown():
        runs.append('teardown')

    benchmark.pedantic(stuff, teardown=teardown)
    assert runs == ['stuff', 'teardown', 'stuff', 'teardown']

    runs = []


def test_args_kwargs(benchmark):
    runs = []

    def stuff(foo, bar=123):
        runs.append((foo, bar))

    benchmark.pedantic(stuff, args=[1], kwargs={'bar': 2})
    assert runs == [(1, 2)]


def test_iterations(benchmark):
    runs = []

    benchmark.pedantic(runs.append, args=[1], iterations=10)
    assert runs == [1] * 11


def test_rounds_iterations(benchmark):
    runs = []

    benchmark.pedantic(runs.append, args=[1], iterations=10, rounds=15)
    assert runs == [1] * 151


def test_rounds(benchmark):
    runs = []

    benchmark.pedantic(runs.append, args=[1], rounds=15)
    assert runs == [1] * 15


def test_warmup_rounds(benchmark):
    runs = []

    benchmark.pedantic(runs.append, args=[1], warmup_rounds=15, rounds=5)
    assert runs == [1] * 20


@pytest.mark.parametrize('value', [0, 'x'])
def test_rounds_must_be_int(benchmark, value):
    runs = []
    with pytest.raises(ValueError):
        benchmark.pedantic(runs.append, args=[1], rounds=value)
    assert runs == []


@pytest.mark.parametrize('value', [-15, 'x'])
def test_warmup_rounds_must_be_int(benchmark, value):
    runs = []
    with pytest.raises(ValueError):
        benchmark.pedantic(runs.append, args=[1], warmup_rounds=value)
    assert runs == []


def test_setup_many_rounds(benchmark):
    runs = []

    def stuff(foo, bar=123):
        runs.append((foo, bar))

    def setup():
        return [1], {'bar': 2}

    benchmark.pedantic(stuff, setup=setup, rounds=10)
    assert runs == [(1, 2)] * 10


def test_teardown_many_rounds(benchmark):
    runs = []

    def stuff():
        runs.append('stuff')

    def teardown():
        runs.append('teardown')

    benchmark.pedantic(stuff, teardown=teardown, rounds=10)
    assert runs == ['stuff', 'teardown'] * 10


def test_teardown_many_iterations(benchmark):
    runs = []

    def stuff():
        runs.append('stuff')

    def teardown():
        runs.append('teardown')

    benchmark.pedantic(stuff, teardown=teardown, iterations=3)
    assert runs == [
        'stuff',
        'stuff',
        'stuff',
        'teardown',  # first round
        'stuff',
        'teardown',  # computing the final result
    ]


def test_cant_use_both_args_and_setup_with_return(benchmark):
    runs = []

    def stuff(foo, bar=123):
        runs.append((foo, bar))

    def setup():
        return [1], {'bar': 2}

    with pytest.raises(TypeError):
        benchmark.pedantic(stuff, setup=setup, args=[123])
    assert runs == []


def test_can_use_both_args_and_setup_without_return(benchmark):
    runs = []

    def stuff(foo, bar=123):
        runs.append((foo, bar))

    benchmark.pedantic(stuff, setup=lambda: None, args=[123])
    assert runs == [(123, 123)]


def test_cant_use_setup_with_many_iterations(benchmark):
    with pytest.raises(ValueError):
        benchmark.pedantic(None, setup=lambda: None, iterations=2)


@pytest.mark.parametrize('value', [0, -1, 'asdf'])
def test_iterations_must_be_positive_int(benchmark, value):
    with pytest.raises(ValueError):
        benchmark.pedantic(None, setup=lambda: None, iterations=value)


@pytest.mark.parametrize('use_setup', [False, True])
@pytest.mark.parametrize('disabled', [False, True])
def test_teardown_with_disabled_benchmark(benchmark, disabled, use_setup):
    benchmark.disabled = disabled
    events = []
    value = []
    result = object()

    def setup():
        events.append('setup')
        return (value,), {'item': 123}

    def target(values, *, item):
        events.append('target')
        values.append(item)
        return result

    def teardown(values, *, item):
        events.append('teardown')
        assert values is value
        assert values.pop() == item

    options = {'setup': setup} if use_setup else {'args': (value,), 'kwargs': {'item': 123}}
    assert benchmark.pedantic(target, teardown=teardown, **options) is result
    assert events == (['setup'] if use_setup else []) + ['target', 'teardown']
    assert value == []


def test_disabled_teardown_runs_once(benchmark):
    benchmark.disabled = True
    events = []
    result = benchmark.pedantic(
        lambda: events.append('target'),
        teardown=lambda: events.append('teardown'),
        rounds=3,
        iterations=2,
        warmup_rounds=4,
    )
    assert result is None
    assert events == ['target', 'teardown']
    assert benchmark.stats is None


def test_disabled_teardown_error(benchmark):
    benchmark.disabled = True

    def teardown():
        raise ValueError('teardown failed')

    with pytest.raises(ValueError, match='teardown failed'):
        benchmark.pedantic(lambda: 123, teardown=teardown)
    assert benchmark.has_error
