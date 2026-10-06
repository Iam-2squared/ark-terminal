"""Single insertion in native V5: remove VETO before picked/occupancy/allocation."""
import ast, inspect, sys
from rneg_io import V5
sys.path.insert(0,str(V5))
import replay as native

def make_engine(defense):
    tree=ast.parse(inspect.getsource(native.day_replay))
    class Insert(ast.NodeTransformer):
        def __init__(self):self.insertions=0
        def visit_Expr(self,node):
            # Exactly the eligible.append((r,d)) point following native checks.
            if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and isinstance(node.value.func.value,ast.Name) and node.value.func.value.id=='eligible' and node.value.func.attr=='append':
                self.insertions+=1
                new=ast.parse("""decision = defense(r)
d['defense_action'] = decision
if decision == 'VETO_THIS_ENTRY':
    d['reason'] = 'RNEG_DEFENSE_VETO'
    continue
""").body
                return new+[node]
            return node
    insert=Insert();tree=insert.visit(tree);assert insert.insertions==1
    ast.fix_missing_locations(tree);namespace=dict(native.day_replay.__globals__,defense=defense)
    exec(compile(tree,'<V5_RNEG_DEFENSE_V1>','exec'),namespace)
    return namespace['day_replay']
