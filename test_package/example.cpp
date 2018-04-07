#include <iostream>
#include <apr_uuid.h>

int main() {
    apr_uuid_t uuid;
    apr_uuid_get(&uuid);
    char* buffer = new char[APR_UUID_FORMATTED_LENGTH + 1];
    apr_uuid_format(buffer, &uuid);
    std::cout << std::string(buffer, APR_UUID_FORMATTED_LENGTH).c_str() << std::endl;
    delete[] buffer;
}
