#include <iostream>

extern "C" {
    double average(double, double);
}

int main() {
    std::cout << "average of 3.0 and 4.0: " << average(3.0, 4.0) << std::endl;
}

/**
 * $ clang++ test_object_code.cpp average.o -o test_object_code.exe
 *
 * $ .\test_object_code.exe
 * average of 3.0 and 4.0: 3.5
 *
 */
