
class Object_Wrapper(object):
    attribute = None

    """A abstract class, used to implements actual ec2 objects"""
    def __init__(self, context, **kwargs):
        self.context = context
