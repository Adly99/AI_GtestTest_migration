#pragma once

#include <gmock/gmock.h>

namespace sdk {
namespace db {

class IDatabase {
public:
    IDatabase() = default;
    virtual ~IDatabase() = default;

    MOCK_METHOD(bool, Connect, (const std::string& connection_string));
    MOCK_METHOD(void, Disconnect, ());
    MOCK_METHOD(std::string, ExecuteQuery, (const std::string& sql), (const));
    MOCK_METHOD(std::vector < std::string >, FetchRows, (int limit));
    MOCK_METHOD(void, UpdateRecord, (int id, const std::string& data));
};

}  // namespace db
}  // namespace sdk
