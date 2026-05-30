#ifndef CODING_RBC_INTERFACES_H
#define CODING_RBC_INTERFACES_H

#include "sys.h"
#include "PVISParamCFG.h"

namespace config
{

void GetPvisCfgData(struct PVISParamCFG& pvis_rbc_data);
void GetCarInfoData(struct carInfo& car_info_rbc_data);
bool IsCarInfoCfgUpdated();

constexpr std::uint32_t GetExtrinsicsSerlSize()
{
    return 100;
}

} // namespace config

#endif // CODING_RBC_INTERFACES_H
