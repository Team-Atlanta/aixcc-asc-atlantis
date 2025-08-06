#include <stdint.h>
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

// Checksum function for additional complexity
uint32_t calculate_checksum(const uint8_t *data, size_t start, size_t end) {
    uint32_t checksum = 0;
    for (size_t i = start; i < end; ++i) {
        checksum += data[i];
        checksum ^= (checksum << 5) + (checksum >> 2) + data[i];
    }
    return checksum;
}

// Deeply hidden condition checker
int hidden_function_level4(const uint8_t *data, size_t size) {
    if (size < 50) {
        return 0;
    }

    uint32_t checksum = calculate_checksum(data, 40, 50);
    if (checksum == 0x12345678) {
        if ((data[40] & data[41]) == 0x3F && (data[42] ^ data[43]) == 0xA5) {
            if ((data[44] + data[45]) == 0x7E && (data[46] - data[47]) == 0x2C) {
                if ((data[48] | data[49]) == 0xDF) {
                    return 1; // Deepest hidden condition met
                }
            }
        }
    }

    return 0;
}

// Intermediate hidden condition checker
int hidden_function_level3(const uint8_t *data, size_t size) {
    if (size < 40) {
        return 0;
    }

    uint32_t checksum = calculate_checksum(data, 30, 40);
    if (checksum == 0x87654321) {
        if ((data[30] ^ data[31]) == 0x2A && (data[32] + data[33]) == 0x92) {
            if ((data[34] - data[35]) == 0x0F && (data[36] | data[37]) == 0xF3) {
                if ((data[38] & data[39]) == 0x5A) {
                    return hidden_function_level4(data, size);
                }
            }
        }
    }

    return 0;
}

// Initial hidden condition checker
int hidden_function_level2(const uint8_t *data, size_t size) {
    if (size < 30) {
        return 0;
    }

    uint32_t checksum = calculate_checksum(data, 20, 30);
    if (checksum == 0xABCDEF01) {
        if ((data[20] ^ data[21]) == 0x3B && (data[22] + data[23]) == 0x83) {
            if ((data[24] - data[25]) == 0x1E && (data[26] | data[27]) == 0xC7) {
                if ((data[28] & data[29]) == 0x6D) {
                    return hidden_function_level3(data, size);
                }
            }
        }
    }

    return 0;
}

// Hidden condition checker
int hidden_function(const uint8_t *data, size_t size) {
    if (size < 20) {
        return 0;
    }

    uint32_t checksum = calculate_checksum(data, 10, 20);
    if (checksum == 0x1234ABCD) {
        if (data[10] == 'K' && data[11] == 'L') {
            if (data[12] == 'M' && data[13] == 'N') {
                if (data[14] == 'O' && data[15] == 'P') {
                    if (data[16] == 'Q' && data[17] == 'R') {
                        if (data[18] == 'S' && data[19] == 'T') {
                            return hidden_function_level2(data, size);
                        }
                    }
                }
            }
        }
    }

    return 0;
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Ensure there is enough data to check all conditions
    if (size < 10) {
        return 0;
    }

    if (data[0] == 'A') {
        if (data[1] == 'B') {
            if (data[2] == 'C') {
                if (data[3] == 'D') {
                    if (data[4] == 'E') {
                        if (data[5] == 'F') {
                            if (data[6] == 'G') {
                                if (data[7] == 'H') {
                                    if (data[8] == 'I') {
                                        if (data[9] == 'J') {
                                            // Additional obfuscated conditions
                                            int hidden_result = hidden_function(data, size);
                                            if (hidden_result) {
                                                printf("Deeply nested condition met with complex hidden conditions! Crashing now.\n");
                                                abort(); // This will crash the program
                                            } else {
                                                printf("Failed at hidden condition\n");
                                            }
                                        } else {
                                            printf("Failed at 10th condition\n");
                                        }
                                    } else {
                                        printf("Failed at 9th condition\n");
                                    }
                                } else {
                                    printf("Failed at 8th condition\n");
                                }
                            } else {
                                printf("Failed at 7th condition\n");
                            }
                        } else {
                            printf("Failed at 6th condition\n");
                        }
                    } else {
                        printf("Failed at 5th condition\n");
                    }
                } else {
                    printf("Failed at 4th condition\n");
                }
            } else {
                printf("Failed at 3rd condition\n");
            }
        } else {
            printf("Failed at 2nd condition\n");
        }
    } else {
        printf("Failed at 1st condition\n");
    }

    return 0;  // Non-zero return values are reserved for signaling failures
}

