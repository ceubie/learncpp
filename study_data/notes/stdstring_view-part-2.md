When printString(s) is called, str makes an expensive copy of s. The function prints the copied string and then destroys it.

Note that s is already holding the string we want to print. Could we just use the string that s is holding instead of making a copy? The answer is possibly -- there are three criteria we need to assess:

Could s be destroyed while str is still using it? No, str dies at the end of the function, and s exists in the scope of the caller and can’t be destroyed before the function returns.
Could s be modified while str is still using it? No, str dies at the end of the function, and the caller has no opportunity to modify the s before the function returns.
Does str modify the string in some way that the caller would not expect? No, the function does not modify the string at all.
Since all three of these criteria are false, there is no risk in using the string that s is holding instead of making a copy. And since string copies are expensive, why pay for one that we don’t need?