import numpy as np

class MyTensor:
    def __init__(self, data, requires_grad=True, grad_fn=None):
        if not isinstance(data, np.ndarray):
            if isinstance(data, list):
                data = np.array(data)
                self.shape = data.shape
            elif isinstance(data, (int, float, np.int8, np.int16, np.int32, np.int64, np.float16, np.float32, np.float64)):
                # data = data
                self.shape = (None, )
            else:
                raise TypeError("Data type not supported")
        else:
            self.shape = data.shape
        self.data = data
        self.requires_grad = requires_grad
        self.grad = np.zeros_like(data) if requires_grad else None  # Gradient of the output with respect to this tensor
        self.grad_fn = grad_fn
        self.children = []  # Upstream nodes

    def backward(self, grad=None, start_point=True):  # start_point is used to determine whether the point is the end of a computation graph
        if not self.requires_grad:
            raise RuntimeError("Cannot compute gradient on tensor that does not require grad")
        # if self.shape[0] and start_point:
        #     raise RuntimeError("Grad can only be created for scalar outputs")
        if start_point:
            self.grad = np.ones_like(self.data)
        if self.grad_fn and len(self.children) > 0:
            self.grad_fn(self)
            for child in self.children:  # DFS
                if isinstance(child, MyTensor) and child.requires_grad:
                    child.backward(grad, start_point=False)

        
    # This function is used to add a gradient calculation function to the tensor
    def add_grad_fn(self, fn):
        self.grad_fn = fn

    # Treat tensor (left) adding("+")
    def __add__(self, other):
        if isinstance(other, (int, float, np.int8, np.int16, np.int32, np.int64, np.float16, np.float32, np.float64)):
            result_data = self.data + other
        elif isinstance(other, MyTensor):
            result_data = self.data + other.data
        else:
            raise TypeError("Unsupported operand type(s) for +: '{}' and '{}'".format(type(self), type(other)))
        requires_grad = self.requires_grad or (hasattr(other, 'requires_grad') and other.requires_grad)  # Requires grad if either operand requires grad
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self, other]
            def add_grad_fn_backward(self):  # Define the local gradient calculation function. Note that self here is the result tensor
                grad = self.grad
                C1 = self.children[0]
                C2 = self.children[1]
                if C1.requires_grad:
                    local = np.ones_like(C1.data)
                    accume = grad * local
                    if isinstance(C2, MyTensor):
                        if not C1.shape[0] or C1.shape == (1, ):  # If C1 is scalar, sum the gradient
                            accume = accume.sum()
                        elif len(C1.shape) == 1 and len(C2.shape) == 2:  # If C1 is a vector and C2 is a matrix
                            accume = np.sum(accume, axis=0, keepdims=False)
                    if len(C1.children) == 0:  # If C1 is a leaf node
                        C1.grad += accume
                    else:
                        C1.grad = accume
                if (hasattr(C2, 'requires_grad')) and C2.requires_grad:
                    local = np.ones_like(C2.data)
                    accume = grad * local
                    if not C2.shape[0] or C2.shape == (1, ):
                        accume = accume.sum()
                    elif len(C2.shape) == 1 and len(C1.shape) == 2:
                        accume = np.sum(accume, axis=0, keepdims=False)
                    if len(C2.children) == 0:
                        C2.grad += accume
                    else:
                        C2.grad = accume
            result.add_grad_fn(add_grad_fn_backward)
        return result
    # Treat tensor (right) adding
    def __radd__(self, other):  # Same as __add__ but for right addition
        return self.__add__(self, other)
    
    def neg(self):  # Negation
        result_data = -self.data
        requires_grad = self.requires_grad
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self]
            def neg_grad_fn_backward(self):
                grad = self.grad
                local = -1
                accum = local * grad
                if len(self.children[0].children) == 0:
                    self.children[0].grad += accum
                else:
                    self.children[0].grad = accum
            result.add_grad_fn(neg_grad_fn_backward)
        return result
    
    def pos(self):  # Positive
        result_data = abs(self.data)
        requires_grad = self.requires_grad
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self]
            def pos_grad_fn_backward(self):
                grad = self.grad
                local = np.sign(self.children[0].data)
                accum = local * grad
                if len(self.children[0].children) == 0:
                    self.children[0].grad += accum
                else:
                    self.children[0].grad = accum
            result.add_grad_fn(pos_grad_fn_backward)
        return result
    
    def __sub__(self, other):  # Subtraction
        if isinstance(other, (int, float, np.int8, np.int16, np.int32, np.int64, np.float16, np.float32, np.float64)):
            other_neg = -other
        elif isinstance(other, MyTensor):
            other_neg = other.neg()
        else:
            raise TypeError("Unsupported operand type(s) for -: '{}' and '{}'".format(type(self), type(other)))
        return self.__add__(other_neg)

    def __rsub__(self, other):  # Same as __sub__ but for right subtraction
        self_neg = self.neg()
        return self_neg.__add__(other)

    def __mul__(self, other):  # Multiplication with scalar
        # The other operand must be a scalar tensor of size (1, ) or (None, ) or a number or a row vector or a column vector
        if isinstance(other, (int, float, np.int8, np.int16, np.int32, np.int64, np.float16, np.float32, np.float64)):
            result_data = self.data * other
        elif isinstance(other, MyTensor):
            result_data = self.data * other.data
        else:
            raise TypeError("Unsupported operand type(s) for *: '{}' and '{}'. Only allow multipliation between tensor and scalar.".format(type(self), type(other)))
        requires_grad = self.requires_grad or (hasattr(other, 'requires_grad') and other.requires_grad)
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self, other]
            def mul_grad_fn_backward(self):
                grad = self.grad
                C1 = self.children[0]
                C2 = self.children[1]
                if C1.requires_grad:
                    if isinstance(C2, (int, float, np.int8, np.int16, np.int32, np.int64, np.float16, np.float32, np.float64)):
                        multiplier = C2
                    elif isinstance(other, MyTensor):
                        multiplier = other.data
                    local = multiplier
                    accume = grad * local
                    if len(C1.children) == 0:
                        C1.grad += accume
                    else:
                        C1.grad = accume
                if (hasattr(C2, 'requires_grad')) and C2.requires_grad:
                    local = C1.data
                    if C2.shape[0]:
                        accume = np.sum(grad * local, axis=len(C2.shape) - 1, keepdims=True)
                    else:  # C2 is a tensor of size (None, )
                        accume = np.sum(grad * local)
                    if C2.shape == (1, ):  # If the shape is scalar of size(1, ), sum the gradient
                        accume = accume.sum(keepdims=False).reshape(C2.shape)
                    elif len(C2.shape) == 1 and C2.shape[0]:  # C2 is a vector
                        accume = accume.reshape(C2.shape)  # This is beacause of using keepdims=True in above. Here we reduce the dimension.
                    if len(C2.children) == 0:
                        C2.grad += accume
                    else:
                        C2.grad = accume
            result.add_grad_fn(mul_grad_fn_backward)
        return result
    
    def __rmul__(self, other):  # Same as __mul__ but for right multiplication
        return self.__mul__(other)
    
    def __getitem__(self, index):  # Indexing
        result_data = self.data[index]
        requires_grad = self.requires_grad
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self]
            def getitem_grad_fn_backward(self):
                grad = self.grad
                C1 = self.children[0]
                local = np.zeros_like(C1.data)
                local[index] = grad
                if len(C1.children) == 0:
                    C1.grad += local
                else:
                    C1.grad = local
            result.add_grad_fn(getitem_grad_fn_backward)
        return result
    
    def __len__(self):  # Length of the tensor
        return self.shape[0]

    def inv(self):  # Inverse(supported for tensor of any shape)
        result_data = 1 / self.data
        requires_grad = self.requires_grad
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self]
            def inv_grad_fn_backward(self):
                grad = self.grad
                local = -1 / (self.children[0].data ** 2)
                accume = local * grad
                if len(self.children[0].children) == 0:
                    self.children[0].grad += accume
                else:
                    self.children[0].grad = accume
            result.add_grad_fn(inv_grad_fn_backward)
        return result   

    # Treat tensor summation(only consider vector summation, because the task does not require matrix summation)
    def sum(self, axis=None):  # Note that this functions do not reshape the tensor
        result = MyTensor(np.sum(self.data, axis=axis, keepdims=True), requires_grad=self.requires_grad)
        if self.requires_grad:
            result.children = [self]
            def sum_grad_fn_backward(self):
                grad = self.grad
                local = np.ones_like(self.children[0].data)
                accume = local * grad
                if len(self.children[0].children) == 0:
                    self.children[0].grad += accume
                else:
                    self.children[0].grad = accume
            result.add_grad_fn(sum_grad_fn_backward)
        return result
    
    # Square of the tensor
    def square(self):
        result_data = self.data ** 2
        requires_grad = self.requires_grad
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self]
            def square_grad_fn_backward(self):
                grad = self.grad
                local = 2 * self.children[0].data
                accume = grad * local
                if len(self.children[0].children) == 0:
                    self.children[0].grad += accume
                else:
                    self.children[0].grad = accume
            result.add_grad_fn(square_grad_fn_backward)
        return result
    
    def sqrt(self):  # Square root
        result_data = np.sqrt(self.data)
        requires_grad = self.requires_grad
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self]
            def sqrt_grad_fn_backward(self):
                grad = self.grad
                local = 0.5 / np.sqrt(self.children[0].data)
                accume = grad * local
                if len(self.children[0].children) == 0:
                    self.children[0].grad += accume
                else:
                    self.children[0].grad = accume
            result.add_grad_fn(sqrt_grad_fn_backward)
        return result

    def item(self):  # Reduce the tensor to a 0-dim tensor scalar
        if self.shape != (1, ) and self.shape != (1, 1) and self.shape != (None,):
            raise ValueError("The tensor is not a scalar")
        requires_grad = self.requires_grad
        result = MyTensor(self.data.item(), requires_grad=requires_grad)
        if requires_grad:
            result.children = [self]
            def item_grad_fn_backward(self):
                grad = self.grad
                if len(self.children[0].children) == 0:
                    self.children[0].grad += grad
                else:
                    self.children[0].grad = np.full(self.children[0].shape, grad)
            result.add_grad_fn(item_grad_fn_backward)
        return result

    def up_dim(self):  # Increase the dimension of the tensor by one
        result_data = np.expand_dims(self.data, axis=0)
        requires_grad = self.requires_grad
        result = MyTensor(result_data, requires_grad=requires_grad)
        if requires_grad:
            result.children = [self]
            def up_dim_grad_fn_backward(self):
                grad = self.grad[0]
                local = np.ones_like(self.children[0].data)
                accume = grad * local
                if len(self.children[0].children) == 0:
                    self.children[0].grad += accume
                else:
                    self.children[0].grad = accume
            result.add_grad_fn(up_dim_grad_fn_backward)
        return result
                

    def __repr__(self):
        return f"MyTensor({self.data})"



# matrix multiplication
def matmul(A, B):
    if not(isinstance(A, MyTensor) and isinstance(B, MyTensor)):
        raise TypeError("Unsupported operand type(s) for matmul: '{}' and '{}'".format(type(A), type(B)))
    # The strict matrix multiplication requires the number of columns of the first matrix to be equal to the number of rows of the second matrix
    if len(A.shape) == 2 and len(B.shape) == 2:
        if A.shape[1] != B.shape[0]:
                raise ValueError("Matrix dimensions do not match")
        requires_grad = A.requires_grad or B.requires_grad
        result = MyTensor(data=np.dot(A.data, B.data), requires_grad=requires_grad)
        if requires_grad:
            result.children = [A, B]
            def matmul_grad_fn_backward(self):
                grad = self.grad
                if A.requires_grad:
                    local = B.data.T
                    if len(A.children) == 0:
                        A.grad += np.dot(grad, local)
                    else:
                        A.grad = np.dot(grad, local)
                if B.requires_grad:
                    local = A.data.T
                    if len(B.children) == 0:
                        B.grad += np.dot(local, grad)
                    else:
                        B.grad = np.dot(local, grad)
            result.add_grad_fn(matmul_grad_fn_backward)
    elif len(A.shape) == 1 and len(B.shape) == 1:  # Allows the dot product of two vectors(1D tensors), not strict matrix multiplication
        result = MyTensor(data=np.dot(A.data, B.data), requires_grad=A.requires_grad or B.requires_grad)
        requires_grad = A.requires_grad or B.requires_grad
        if requires_grad:
            result.children = [A, B]
            def matmul_grad_fn_backward(self):
                grad = self.grad
                C1 = self.children[0]
                C2 = self.children[1]
                if C1.requires_grad:
                    local = C2.data
                    if len(C1.children) == 0:
                        C1.grad += grad * local
                    else:
                        C1.grad = grad * local
                if C2.requires_grad:
                    local = C1.data
                    if len(C2.children) == 0:
                        C2.grad += grad * local
                    else:
                        C2.grad = grad * local
            result.add_grad_fn(matmul_grad_fn_backward)
    else:
        raise ValueError("Matrix dimensions do not match：{} and {}".format(A.shape, B.shape))
    return result


# exponential
def exp(x):
    result = MyTensor(np.exp(x.data), requires_grad=x.requires_grad)
    if x.requires_grad:
        result.children = [x]
        def exp_grad_fn_backward(self):
            grad = self.grad
            local = self.data
            if len(self.children[0].children) == 0:
                self.children[0].grad += grad * local
            else:
                self.children[0].grad = grad * local
        result.add_grad_fn(exp_grad_fn_backward)
    return result



# logarithm
def log(x):
    result = MyTensor(np.log(x.data), requires_grad=x.requires_grad)
    if x.requires_grad:
        result.children = [x]
        def log_grad_fn_backward(self):
            grad = self.grad
            local = 1 / self.children[0].data
            if len(self.children[0].children) == 0:
                self.children[0].grad += grad * local
            else:
                self.children[0].grad = grad * local
        result.add_grad_fn(log_grad_fn_backward)
    return result
