"""feedback.py

Utility classes for fetching externalized strings stored as dicts.

Example:
    FEEDBACK = {
        'hello': 'Hello World!',
        'breakfast': 'Menu: {}, {}, {}'
    }
    fb = FeedbackGetter(FEEDBACK)

    print(FEEDBACK.hello)
    # 'Hello World!'

    print(FEEDBACK.breakfast('spam', 'eggs', 'ham')
    # 'Menu: spam, eggs, ham'
"""

class FeedbackGetter:
    """Attribute-like access to dict-based external strings"""

    def __init__(self, msg_dict):
        self.msg_dict = msg_dict

    def __getattr__(self, label):
        if label not in self.msg_dict:
            raise KeyError('could not find any feedback item labelled '
                           f'{label}')
        return FormatString(self.msg_dict[label])


class FormatString(str):
    """Allows strings to be called, passing args directly to str.format()

    Example:
        s = FormatString('Menu: {}, {}, {}')
        m = s('spam', 'eggs', 'ham')
        print(m)
        # 'Menu: spam, eggs, ham'
    """

    def __call__(self, *args, **kwargs):
        return self.format(*args, **kwargs)
