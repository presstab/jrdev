class CodeTaskCancelled(Exception):
    """
    Exception to signal that the code task was cancelled by the user.
    """
    pass

class Reprompt(Exception):
    """
    Exception to signal that the user has sent a new prompt
    """
    pass