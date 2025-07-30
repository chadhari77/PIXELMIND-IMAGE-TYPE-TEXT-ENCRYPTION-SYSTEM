#include <stdio.h>

int square(int x) {
    return x * x;
}

int main() {
    int num = 5;
    printf("The square of %d is %d\n", num, square(num));
    return 0;
}
