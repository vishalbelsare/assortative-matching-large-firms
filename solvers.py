import numpy as np
from scipy import integrate, special
import sympy as sym

import models

# represent endogenous variables mu and theta as a deferred vector
V = sym.DeferredVector('V')


class ShootingSolver(object):
    """Solves a model using forward shooting."""

    __numeric_jacobian = None

    __numeric_system = None

    __numeric_wage = None

    __integrator = None

    _modules = [{'ImmutableMatrix': np.array, 'erf': special.erf}, 'numpy']

    def __init__(self, model):
        """
        Create an instance of the ShootingSolver class.

        """
        self.model = model

    @property
    def _numeric_jacobian(self):
        """
        Vectorized function for numerical evaluation of model Jacobian.

        :getter: Return the current function for evaluating the Jacobian.
        :type: function

        """
        if self.__numeric_jacobian is None:
            self.__numeric_jacobian = sym.lambdify(self._symbolic_args,
                                                   self._symbolic_jacobian,
                                                   self._modules)
        return self.__numeric_jacobian

    @property
    def _numeric_system(self):
        """
        Vectorized function for numerical evaluation of model system.

        :getter: Return the current function for evaluating the system.
        :type: function

        """
        if self.__numeric_system is None:
            self.__numeric_system = sym.lambdify(self._symbolic_args,
                                                 self._symbolic_system,
                                                 self._modules)
        return self.__numeric_system

    @property
    def _numeric_wage(self):
        """
        Vectorized function for numerical evaluation of wages.

        :getter: Return the current function for evaluating wages.
        :type: function

        """
        if self.__numeric_wage is None:
            self.__numeric_wage = sym.lambdify(self._symbolic_args,
                                               self._symbolic_wage,
                                               self._modules)
        return self.__numeric_wage

    @property
    def _symbolic_args(self):
        """
        Symbolic arguments used when lambdifying symbolic Jacobian and system.

        :getter: Return the list of symbolic arguments.
        :type: list

        """
        return self._symbolic_variables + self._symbolic_params

    @property
    def _symbolic_equations(self):
        """
        Symbolic expressions defining the right-hand side of a system of ODEs.

        :getter: Return the list of symbolic expressions.
        :type: list

        """
        return [self.model.matching.mu_prime, self.model.matching.theta_prime]

    @property
    def _symbolic_jacobian(self):
        """
        Symbolic expressions defining the Jacobian of a system of ODEs.

        :getter: Return the symbolic Jacobian.
        :type: sympy.Basic

        """
        return self._symbolic_system.jacobian([V[0], V[1]])

    @property
    def _symbolic_params(self):
        """
        Symbolic parameters passed as arguments when lambdifying symbolic
        Jacobian and system.

        :getter: Return the list of symbolic parameter arguments.
        :type: list

        """
        return sym.var(list(self.model.params.keys()))

    @property
    def _symbolic_system(self):
        """
        Symbolic matrix defining the right-hand side of a system of ODEs.

        :getter: Return the symbolic matrix.
        :type: sympy.Matrix

        """
        system = sym.Matrix(self._symbolic_equations)
        return system.subs({'mu': V[0], 'theta': V[1]})

    @property
    def _symbolic_variables(self):
        """
        Symbolic variables passed as arguments when lambdifying symbolic
        Jacobian and system.

        :getter: Return the list of symbolic variable arguments.
        :type: list

        """
        return [self.model.workers.var, V]

    @property
    def _symbolic_wage(self):
        """
        Symbolic expression defining wages.

        :getter: Return the symbolic expression for wages
        :type: sympy.Basic

        """
        wage = self.model.matching.wage
        return wage.subs({'mu': V[0], 'theta': V[1]})

    @property
    def model(self):
        """
        Instance of the models.Model class to be solved via forward shooting.

        :getter: Return the current models.Model instance.
        :setter: Set a new models.Model instance.
        :type: models.Model

        """
        return self._model

    @model.setter
    def model(self, model):
        """Set a new Model attribute."""
        self._model = self._validate_model(model)
        self._clear_cache()

    @property
    def integrator(self):
        """
        Integrator for solving a system of ordinary differential equations.

        :getter: Return the current integrator.
        :type: scipy.integrate.ode

        """
        if self.__integrator is None:
            self.__integrator = integrate.ode(f=self.evaluate_rhs,
                                              jac=self.evaluate_jacobian)
        return self.__integrator

    def _clear_cache(self):
        """Clear cached functions for evaluating the model and its jacobian."""
        self.__numeric_jacobian = None
        self.__numeric_system = None
        self.__solver = None

    def _solve_negative_assortative_matching(self):
        raise NotImplementedError

    def _solve_positive_assortative_matching(self):
        raise NotImplementedError

    @staticmethod
    def _validate_model(model):
        """Validate the model attribute."""
        if not isinstance(model, models.Model):
            mesg = ("Attribute 'model' must have type models.Model, not {}.")
            raise AttributeError(mesg.format(model.__class__))
        else:
            return model

    def evaluate_jacobian(self, x, V):
        r"""
        Numerically evaluate model Jacobian.

        Parameters
        ----------
        x : float
            Value for worker skill (i.e., the independent variable).
        V : numpy.array (shape=(2,))
            Array of values for the dependent variables with ordering:
            :math:`[\mu, \theta]`.

        Returns
        -------
        jac : numpy.array (shape=(2,2))
            Jacobian matrix of partial derivatives.

        """
        jac = self._numeric_jacobian(x, V, **self.model.params)
        return jac

    def evaluate_rhs(self, x, V):
        r"""
        Numerically evaluate right-hand side of the system of ODEs.

        Parameters
        ----------
        x : float
            Value for worker skill (i.e., the independent variable).
        V : numpy.array (shape=(2,))
            Array of values for the dependent variables with ordering:
            :math:`[\mu, \theta]`.

        Returns
        -------
        rhs : numpy.array (shape=(2,))
            Right hand side of the system of ODEs.

        """
        rhs = self._numeric_system(x, V, **self.model.params).ravel()
        return rhs

    def evaluate_wage(self, x, V):
        r"""
        Numerically evaluate wage for a worker with skill level x when matched
        to a firm with productivity V[0] with size V[1].

        Parameters
        ----------
        x : float
            Value for worker skill (i.e., the independent variable).
        V : numpy.array (shape=(2,))
            Array of values for the dependent variables with ordering:
            :math:`[\mu, \theta]`.

        Returns
        -------
        wage : float
            Worker's wage.

        """
        wage = self._numeric_wage(x, V, **self.model.params)
        return wage

    def solve(self):
        if self.model.assortativity == 'positive':
            soln = self._solve_positive_assortative_matching()
        else:
            soln = self._solve_negative_assortative_matching()
        return soln
