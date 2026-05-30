#pragma once

#include <gmock/gmock.h>
#include "IDatabase.h"

namespace sdk {
namespace db {

class MockIDatabase : public IDatabase {
public:
    MOCK_METHOD(bool, Connect, (const std::string& connection_string), (override));
    MOCK_METHOD(void, Disconnect, (), (override));
    MOCK_METHOD(std::string, ExecuteQuery, (const std::string& sql), (const, override));
    MOCK_METHOD(std::vector < std::string >, FetchRows, (int limit), (override));
    MOCK_METHOD(void, UpdateRecord, (int id, const std::string& data), (override));
};

}  // namespace db
}  // namespace sdk
