from transfer_units import Response

class StateMachine:
  def __init__(self, client, global_state):
    self.transitions = {}
    self.start_state = None
    self.end_states = []
    self.current_state = None
    self.global_state = global_state
    self.client = client
  
  def add_transition(self, state_name, command, transition, end_state = 0):
    self.transitions.setdefault(state_name, {})
    self.transitions[state_name][command] = transition
    if end_state:
      self.end_states.append(end_state)

  def set_start(self, name):
      self.start_state = name
      self.current_state = name

  def process_command(self, unpacked_request):
    if self.current_state in self.transitions and unpacked_request.type in self.transitions[self.current_state]:
      handler = self.transitions[self.current_state][unpacked_request.type]
      if not handler:
        return Response(-4, 'Cannot transition from this state')
      else:
        (new_state, response) = handler(unpacked_request, self.global_state, self.client)
        self.current_state = new_state
        return response
    else:
      return Response(-4, 'Client needs to connect first')
    
      