#pragma once
#include <string>
#include <vector>

namespace sdk {
namespace db {

class IDatabase {
public:
    virtual ~IDatabase() = default;

    virtual bool Connect(const std::string& connection_string) = 0;
    virtual void Disconnect() = 0;
    
    virtual std::string ExecuteQuery(const std::string& sql) const = 0;
    virtual std::vector<std::string> FetchRows(int limit) = 0;
    
    virtual void UpdateRecord(int id, const std::string& data) = 0;
};

}  // namespace db
}  // namespace sdk
