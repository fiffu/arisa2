from collections import OrderedDict
import random


class Puddle:
    DISTRIBUTIONS = {
        'uniform': random.uniform,
        'gaussian': random.gauss,
    }

    def __init__(self):
        self._components = OrderedDict()
        self.colspace = None


    @classmethod
    def wrap(cls, value):
        return value % 1


    @classmethod
    def clamp(cls, value):
        return min(max(value, 0), 1)


    @classmethod
    def roll(cls, distribution, p1, p2):
        func = self.DISTRIBUTIONS.get(distribution)
        if not func:
            return 0
        return func(p1, p2)


    def __getattr__(self, component_name):
        if component_name in self._components:
            return self._components[component_name]


    def add_component(self,
                      component_name: str,
                      normalize_mode: str,
                      distribution: str,
                      param1: float,
                      param2: float):
        try:
            name = str(component_name)
            assert component_name not in self._components
        except ValueError:
            raise ValueError('component name must be a string')
        except AssertionError:
            raise ValueError(f'"{component_name}" has already been added '
                             f'as a component')

        args = locals()

        for argname, accepts in [
            'normalize_mode', ('wrap', 'clamp'),
            'distribution', DISTRIBUTIONS.keys(),
        ]:
            if args[argname] not in accepts:
                raise ValueError(f'"{}" must be one of: {", ".join(accepts)}')

        for px in ['param1', 'param2']:
            p = args[px]
            if not (0 <= p and p <= 1):
                raise ValueError(f'value of "{px}" must be in range [0, 1]')

        self._components[component_name] = {'normalize_mode': normalize_mode,
                                            'distribution': distribution,
                                            'param1': param1,
                                            'param2': param2}


        def dip(self):
            out = []
            for component, options in self._components.items():
                rolled = self.roll_component(component, **options)
                out.append(rolled)
            return tuple(out)


        def roll_component(self, component_name, **options):
            if not component_name in self._components:
                raise ValueError(f'no such component: "{component_name}"')

            dist = options['distribution']
            p1 = options['param1']
            p2 = options['param2']

            value = self.roll(dist, p1, p2)

            norm_method = getattr(self, options['normalize_mode'])
            value =  norm_method(value)

            return value



class HsvPuddle(Puddle):
    def __init__(self,
                 h_dist, h_param1, h_param2,
                 s_dist, s_param1, s_param2,
                 v_dist, v_param1, v_param2):
        super().__init__(self)
        self.colspace = 'hsv'
        self.add_component('h', 'wrap', h_dist, h_param1, h_param2)
        self.add_component('s', 'clamp', s_dist, s_param1, s_param2)
        self.add_component('v', 'clamp', v_dist, v_param1, v_param2)



class RgbPuddle(Puddle):
    def __init__(self,
                 r_dist, r_param1, r_param2,
                 g_dist, g_param1, g_param2,
                 b_dist, b_param1, b_param2):
        super().__init__(self)
        self.colspace = 'rgb'
        self.add_component('r', 'clamp', r_dist, r_param1, r_param2)
        self.add_component('g', 'clamp', g_dist, g_param1, g_param2)
        self.add_component('b', 'clamp', b_dist, b_param1, b_param2)



class StaticPuddle:
    def __init__(self, cls_pool, component1, component2, component3):
        cls_pool.__init__(self,
                          'uniform', component1, component1,
                          'uniform', component2, component2,
                          'uniform', component3, component3)



class Pool:
    def __init__(self):
        self._puddles = []


    def add_puddle(self, puddle, weight):
        try:
            weight = float(weight)
            assert weight > 0
        except (ValueError, AssertionError):
            msg = 'the "weight" argument should be a positive float value'
            raise ValueError(msg)

        self._puddles.append((puddle, weight))


    def roll(self):
        if not self._puddles:
            raise RuntimeError('cannot roll with Pool without Puddles, must '
                               'call add_puddle() first')
        pud = self._choose_puddle()
        return pud.dip()


    def _choose_puddle(self):
        puds = self._puddles
        weights = [p[1] for p in puds]

        rolled = random.uniform(0, sum(weights))

        pud_by_weight_ascending = sorted(puds, key=lambda p: p[1])
        cumu_wgt = 0

        for pud, weight in pud_by_weight_ascending:
            if cumu_wgt + weight < rolled:
                cumu_wgt += weight
                continue
            return pud
