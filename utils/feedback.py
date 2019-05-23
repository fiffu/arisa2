class FeedbackGetter:
    def __init__(self, error_msg_dict):
        self.error_dict = error_msg_dict
    
    def __getattr__(self, label):
        if label not in self.error_dict:
            raise KeyError('could not find any feedback item labelled '
                           f'{label}')
        return FormatString(self.error_dict[label])


class FormatString(str):
    def __call__(self, *args, **kwargs):
        return self.format(*args, **kwargs)
