from functools import wraps

DEF_IS_ACTION = "_is_action"
DEF_HAS_QUESTION = "_has_question"
DEF_SHOULD_SUMMARIZE = "_should_summarize"

DEF_HAS_CONTEXT = "_has_context"


def action_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    setattr(wrapper, DEF_IS_ACTION, True)
    return wrapper


def action_with_summary(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        question = kwargs.get("question", None)
        setattr(wrapper, DEF_HAS_QUESTION, question)
        return func(*args, **kwargs)

    setattr(wrapper, DEF_IS_ACTION, True)
    return wrapper


def action_with_summary(has_question):
    def inner_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        setattr(wrapper, DEF_IS_ACTION, True)
        setattr(wrapper, DEF_SHOULD_SUMMARIZE, True)
        setattr(wrapper, DEF_HAS_QUESTION, has_question)
        return wrapper

    return inner_decorator


def context_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    setattr(wrapper, DEF_HAS_CONTEXT, True)
    return wrapper
