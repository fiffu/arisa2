import random


class Puddle:
    def __init__(self, *coltuples):
        try:
            selection = []
            for tup in coltuples:
                a, b, c = tup
                selection.append((a, b, c))
        except (ValueError, TypeError) as e:
            msg = f'varargs must be Tuple[float, float, float] ({e})'
            raise ValueError(msg)

        self.selection = selection


    def dip(self):
        if not self.selection:
            r = lambda: random.uniform(0, 1)
            return r(), r(), r()
        return random.choice(self.selection)



class NormalPuddle:
    def __init__(self, hue_mean=0.5, sd=0.05):
        if not (0 <= hue_mean and hue_mean <= 1):
            msg = 'argument hue_mean must be in range 0 <= hue_mean <= 1'
            raise ValueError(msg)

        self.hue_mean = hue_mean
        self.sd = sd


    def dip(self):
        # Generate random number
        val = random.gauss(self.hue_mean, self.sd)
        # Normalize to [0, 1]
        return val % 1



class UniformPuddle:
    def __init__(self,
                 a_low=0, a_high=1,
                 b_low=0, b_high=1,
                 c_low=0, c_high=1):
        loc = locals()

        for name in ['a_low', 'a_high',
                     'b_low', 'b_high',
                     'c_low', 'c_high']:

            var = loc[name]
            if not (0 <= var and var <= 1):
                msg = f'argument {name} must be in range 0 <= {name} <= 1'
                raise ValueError(msg)

            setattr(self, name, var)


    def dip(self):
        unif = random.uniform
        out = []
        for x in 'abc':
            roll = unif(getattr(self, x + '_low'),
                        getattr(self, x + '_high'))
            out.append(roll)
        return tuple(out)



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
