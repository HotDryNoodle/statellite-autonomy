#include "orbit_time.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>

namespace unit::time {
namespace {

constexpr int     kGpsTaiOffsetSeconds  = 19;
constexpr int     kBdtGpsOffsetSeconds  = -14;
constexpr double  kTaiToTtOffsetSeconds = 32.184;
constexpr int64_t kGpsEpochMjdDay       = 44244;
constexpr int64_t kBdtEpochMjdDay       = 53736;

bool NearlyEqual(double a, double b, double tol) {
    return std::fabs(a - b) <= tol;
}

/**
 * @brief 判断年份是否为公历闰年。
 */
bool IsLeapYear(int year) {
    if (year % 400 == 0) { return true; }
    if (year % 100 == 0) { return false; }
    return (year % 4 == 0);
}

/**
 * @brief 返回指定年月对应的天数。
 */
int DaysInMonth(int year, int month) {
    constexpr int kDays[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (month == 2 && IsLeapYear(year)) { return 29; }
    return kDays[month - 1];
}

/**
 * @brief 校验公历日期字段是否在有效范围内。
 */
bool IsCivilDateValid(int year, int month, int day) {
    if (year < 1900 || month < 1 || month > 12) { return false; }
    int dim = DaysInMonth(year, month);
    return day >= 1 && day <= dim;
}

/**
 * @brief 校验 UTC CivilTime 是否满足字段约束。
 */
bool IsCivilTimeValid(const CivilTime& utc) {
    if (!IsCivilDateValid(utc.year, utc.month, utc.day)) { return false; }
    if (utc.hour < 0 || utc.hour > 23) { return false; }
    if (utc.min < 0 || utc.min > 59) { return false; }
    if (utc.sec < 0.0 || utc.sec >= 61.0) { return false; }
    return true;
}

/**
 * @brief 将公历日期转换为 MJD 整日部分。
 */
TimeResult<int64_t> MjdDayFromCivilDate(int year, int month, int day) {
    if (!IsCivilDateValid(year, month, day)) {
        return TimeResult<int64_t>::Error(TimeError::kInvalidCivilTime);
    }
    int     a   = (14 - month) / 12;
    int     y   = year + 4800 - a;
    int     m   = month + 12 * a - 3;
    int64_t jdn = static_cast<int64_t>(day) + (153 * m + 2) / 5 + 365LL * y +
                  y / 4 - y / 100 + y / 400 - 32045;
    int64_t mjd = jdn - 2400001;
    return TimeResult<int64_t>::Ok(mjd);
}

/**
 * @brief 将 MJD 日与日内秒转换为 UTC CivilTime。
 */
TimeResult<CivilTime> CivilFromMjdDay(int64_t mjd_day, double seconds_of_day) {
    if (seconds_of_day < 0.0 || seconds_of_day >= kSecPerDay) {
        return TimeResult<CivilTime>::Error(TimeError::kInvalidCivilTime);
    }
    int64_t jdn   = mjd_day + 2400001;
    int64_t a     = jdn + 32044;
    int64_t b     = (4 * a + 3) / 146097;
    int64_t c     = a - (146097 * b) / 4;
    int64_t d     = (4 * c + 3) / 1461;
    int64_t e     = c - (1461 * d) / 4;
    int64_t m     = (5 * e + 2) / 153;
    int     day   = static_cast<int>(e - (153 * m + 2) / 5 + 1);
    int     month = static_cast<int>(m + 3 - 12 * (m / 10));
    int     year  = static_cast<int>(100 * b + d - 4800 + (m / 10));

    int    hour = static_cast<int>(seconds_of_day / 3600.0);
    double rem  = seconds_of_day - static_cast<double>(hour) * 3600.0;
    int    min  = static_cast<int>(rem / 60.0);
    double sec  = rem - static_cast<double>(min) * 60.0;
    return TimeResult<CivilTime>::Ok(
        CivilTime{year, month, day, hour, min, sec});
}

/**
 * @brief 计算 UTC CivilTime 的日内秒数表示。
 */
TimeResult<double> SecondsOfDayFromCivil(const CivilTime& utc) {
    if (!IsCivilTimeValid(utc)) {
        return TimeResult<double>::Error(TimeError::kInvalidCivilTime);
    }
    if (utc.sec >= 60.0) {
        return TimeResult<double>::Ok(utc.hour * 3600.0 + utc.min * 60.0 +
                                      60.0);
    }
    return TimeResult<double>::Ok(utc.hour * 3600.0 + utc.min * 60.0 + utc.sec);
}

}  // namespace

TimeSys::TimeSys() = default;

void TimeSys::Reset() {
    status_                = TimeStatus::kUninitialized;
    initialized_           = false;
    has_leap_seconds_      = false;
    has_ut1_minus_utc_     = false;
    ut1_minus_utc_seconds_ = 0.0;
    tai_                   = TaiMjd{};
}

void TimeSys::SetLeapSecondTable(const LeapSecondTable& table) {
    leap_seconds_     = table;
    has_leap_seconds_ = table.IsValid();
    if (!has_leap_seconds_) { status_ = TimeStatus::kInvalid; }
}

void TimeSys::SetUt1MinusUtcSeconds(double ut1_minus_utc_seconds) {
    ut1_minus_utc_seconds_ = ut1_minus_utc_seconds;
    has_ut1_minus_utc_     = true;
    if (initialized_ && status_ != TimeStatus::kInvalid) {
        status_ = TimeStatus::kValid;
    }
}

TimeStatus TimeSys::Status() const {
    if (!initialized_) { return TimeStatus::kUninitialized; }
    return status_;
}

TimeError TimeSys::SetUtcCivil(const CivilTime& utc) {
    if (!IsCivilTimeValid(utc)) {
        status_ = TimeStatus::kInvalid;
        return TimeError::kInvalidCivilTime;
    }
    TimeError ready = EnsureReadyForUtc();
    if (ready != TimeError::kOk) {
        status_ = TimeStatus::kInvalid;
        return ready;
    }
    TimeResult<int> tai_minus_utc = leap_seconds_.GetTaiMinusUtcSeconds(utc);
    if (!tai_minus_utc.ok()) {
        status_ = TimeStatus::kInvalid;
        return tai_minus_utc.error;
    }
    TimeResult<int64_t> mjd_day =
        MjdDayFromCivilDate(utc.year, utc.month, utc.day);
    if (!mjd_day.ok()) {
        status_ = TimeStatus::kInvalid;
        return mjd_day.error;
    }
    TimeResult<double> seconds = SecondsOfDayFromCivil(utc);
    if (!seconds.ok()) {
        status_ = TimeStatus::kInvalid;
        return seconds.error;
    }
    double tai_seconds =
        seconds.value + static_cast<double>(tai_minus_utc.value);
    tai_         = TaiMjd{NormalizeMjdSeconds(mjd_day.value, tai_seconds)};
    initialized_ = true;
    status_      = TimeStatus::kValid;
    return TimeError::kOk;
}

TimeError TimeSys::SetUtcMjd(const UtcMjd& utc) {
    if (!IsMjdValid(utc.mjd)) {
        status_ = TimeStatus::kInvalid;
        return TimeError::kInvalidMjd;
    }
    TimeError ready = EnsureReadyForUtc();
    if (ready != TimeError::kOk) {
        status_ = TimeStatus::kInvalid;
        return ready;
    }
    TimeResult<int> tai_minus_utc = leap_seconds_.GetTaiMinusUtcSeconds(utc);
    if (!tai_minus_utc.ok()) {
        status_ = TimeStatus::kInvalid;
        return tai_minus_utc.error;
    }
    double seconds = utc.mjd.frac_day * kSecPerDay +
                     static_cast<double>(tai_minus_utc.value);
    tai_         = TaiMjd{NormalizeMjdSeconds(utc.mjd.day, seconds)};
    initialized_ = true;
    status_      = TimeStatus::kValid;
    return TimeError::kOk;
}

TimeError TimeSys::SetTaiMjd(const TaiMjd& tai) {
    if (!IsMjdValid(tai.mjd)) {
        status_ = TimeStatus::kInvalid;
        return TimeError::kInvalidMjd;
    }
    tai_         = tai;
    initialized_ = true;
    status_      = TimeStatus::kValid;
    return TimeError::kOk;
}

TimeError TimeSys::SetTtMjd(const TtMjd& tt) {
    if (!IsMjdValid(tt.mjd)) {
        status_ = TimeStatus::kInvalid;
        return TimeError::kInvalidMjd;
    }
    double seconds = tt.mjd.frac_day * kSecPerDay - kTaiToTtOffsetSeconds;
    tai_           = TaiMjd{NormalizeMjdSeconds(tt.mjd.day, seconds)};
    initialized_   = true;
    status_        = TimeStatus::kValid;
    return TimeError::kOk;
}

TimeError TimeSys::SetGpst(const GpstTime& gpst) {
    if (gpst.sec < 0.0 || gpst.sec >= kSecPerWeek) {
        status_ = TimeStatus::kInvalid;
        return TimeError::kInvalidWeekSeconds;
    }
    double total_seconds =
        static_cast<double>(gpst.week) * kSecPerWeek + gpst.sec;
    double tai_seconds =
        total_seconds + static_cast<double>(kGpsTaiOffsetSeconds);
    tai_         = TaiMjd{NormalizeMjdSeconds(kGpsEpochMjdDay, tai_seconds)};
    initialized_ = true;
    status_      = TimeStatus::kValid;
    return TimeError::kOk;
}

TimeError TimeSys::SetBdt(const BdtTime& bdt) {
    if (bdt.sec < 0.0 || bdt.sec >= kSecPerWeek) {
        status_ = TimeStatus::kInvalid;
        return TimeError::kInvalidWeekSeconds;
    }
    double total_seconds =
        static_cast<double>(bdt.week) * kSecPerWeek + bdt.sec;
    double tai_seconds =
        total_seconds +
        static_cast<double>(kGpsTaiOffsetSeconds - kBdtGpsOffsetSeconds);
    tai_         = TaiMjd{NormalizeMjdSeconds(kBdtEpochMjdDay, tai_seconds)};
    initialized_ = true;
    status_      = TimeStatus::kValid;
    return TimeError::kOk;
}

TimeResult<UtcMjd> TimeSys::GetUtcMjd() const {
    TimeError ready = EnsureReadyForUtc();
    if (ready != TimeError::kOk) { return TimeResult<UtcMjd>::Error(ready); }
    if (!initialized_) {
        return TimeResult<UtcMjd>::Error(TimeError::kUninitialized);
    }
    TimeResult<CivilTime> civil = leap_seconds_.TaiToUtcCivil(tai_);
    if (!civil.ok()) { return TimeResult<UtcMjd>::Error(civil.error); }
    if (civil.value.sec >= 60.0) {
        return TimeResult<UtcMjd>::Error(TimeError::kInvalidMjd);
    }
    TimeResult<int64_t> mjd_day = MjdDayFromCivilDate(
        civil.value.year, civil.value.month, civil.value.day);
    if (!mjd_day.ok()) { return TimeResult<UtcMjd>::Error(mjd_day.error); }
    TimeResult<double> seconds = SecondsOfDayFromCivil(civil.value);
    if (!seconds.ok()) { return TimeResult<UtcMjd>::Error(seconds.error); }
    return TimeResult<UtcMjd>::Ok(
        UtcMjd{NormalizeMjdSeconds(mjd_day.value, seconds.value)});
}

TimeResult<CivilTime> TimeSys::GetUtcCivil() const {
    TimeError ready = EnsureReadyForUtc();
    if (ready != TimeError::kOk) { return TimeResult<CivilTime>::Error(ready); }
    if (!initialized_) {
        return TimeResult<CivilTime>::Error(TimeError::kUninitialized);
    }
    return leap_seconds_.TaiToUtcCivil(tai_);
}

TimeResult<Ut1Mjd> TimeSys::GetUt1Mjd() const {
    TimeError ready = EnsureReadyForUt1();
    if (ready != TimeError::kOk) { return TimeResult<Ut1Mjd>::Error(ready); }
    TimeResult<UtcMjd> utc = GetUtcMjd();
    if (!utc.ok()) { return TimeResult<Ut1Mjd>::Error(utc.error); }
    MjdTime ut1 = utc.value.mjd;
    ut1.frac_day += ut1_minus_utc_seconds_ / kSecPerDay;
    ut1 = NormalizeMjdSeconds(ut1.day, ut1.frac_day * kSecPerDay);
    return TimeResult<Ut1Mjd>::Ok(Ut1Mjd{ut1});
}

TimeResult<TaiMjd> TimeSys::GetTaiMjd() const {
    if (!initialized_) {
        return TimeResult<TaiMjd>::Error(TimeError::kUninitialized);
    }
    return TimeResult<TaiMjd>::Ok(tai_);
}

TimeResult<TtMjd> TimeSys::GetTtMjd() const {
    if (!initialized_) {
        return TimeResult<TtMjd>::Error(TimeError::kUninitialized);
    }
    MjdTime tt = tai_.mjd;
    tt.frac_day += kTaiToTtOffsetSeconds / kSecPerDay;
    tt = NormalizeMjdSeconds(tt.day, tt.frac_day * kSecPerDay);
    return TimeResult<TtMjd>::Ok(TtMjd{tt});
}

TimeResult<GpstTime> TimeSys::GetGpst() const {
    if (!initialized_) {
        return TimeResult<GpstTime>::Error(TimeError::kUninitialized);
    }
    double tai_seconds =
        static_cast<double>(tai_.mjd.day - kGpsEpochMjdDay) * kSecPerDay +
        tai_.mjd.frac_day * kSecPerDay;
    double gpst_seconds =
        tai_seconds - static_cast<double>(kGpsTaiOffsetSeconds);
    if (gpst_seconds < 0.0) {
        return TimeResult<GpstTime>::Error(TimeError::kOutOfRange);
    }
    uint32_t week =
        static_cast<uint32_t>(std::floor(gpst_seconds / kSecPerWeek));
    double sec = gpst_seconds - static_cast<double>(week) * kSecPerWeek;
    return TimeResult<GpstTime>::Ok(GpstTime{week, sec});
}

TimeResult<BdtTime> TimeSys::GetBdt() const {
    if (!initialized_) {
        return TimeResult<BdtTime>::Error(TimeError::kUninitialized);
    }
    double tai_seconds =
        static_cast<double>(tai_.mjd.day - kBdtEpochMjdDay) * kSecPerDay +
        tai_.mjd.frac_day * kSecPerDay;
    double bdt_seconds =
        tai_seconds -
        static_cast<double>(kGpsTaiOffsetSeconds - kBdtGpsOffsetSeconds);
    if (bdt_seconds < 0.0) {
        return TimeResult<BdtTime>::Error(TimeError::kOutOfRange);
    }
    uint32_t week =
        static_cast<uint32_t>(std::floor(bdt_seconds / kSecPerWeek));
    double sec = bdt_seconds - static_cast<double>(week) * kSecPerWeek;
    return TimeResult<BdtTime>::Ok(BdtTime{week, sec});
}

bool TimeSys::IsMjdValid(const MjdTime& mjd) {
    if (mjd.frac_day < 0.0 || mjd.frac_day >= 1.0) { return false; }
    if (!std::isfinite(mjd.frac_day)) { return false; }
    return true;
}

MjdTime TimeSys::NormalizeMjdSeconds(int64_t day, double seconds) {
    double day_offset = std::floor(seconds / kSecPerDay);
    double rem        = seconds - day_offset * kSecPerDay;
    if (rem < 0.0) {
        day_offset -= 1.0;
        rem += kSecPerDay;
    }
    MjdTime result{};
    result.day      = day + static_cast<int64_t>(day_offset);
    result.frac_day = rem / kSecPerDay;
    if (NearlyEqual(result.frac_day, 1.0, 1e-12)) {
        result.day += 1;
        result.frac_day = 0.0;
    }
    return result;
}

TimeError TimeSys::EnsureReadyForUtc() const {
    if (!has_leap_seconds_) { return TimeError::kMissingLeapSeconds; }
    return TimeError::kOk;
}

TimeError TimeSys::EnsureReadyForUt1() const {
    if (!has_ut1_minus_utc_) { return TimeError::kMissingUt1Utc; }
    if (!has_leap_seconds_) { return TimeError::kMissingLeapSeconds; }
    return TimeError::kOk;
}

TimeResult<std::chrono::duration<double>> TimeSys::operator-(
    const TimeSys& other) const {
    if (!initialized_ || !other.initialized_) {
        return TimeResult<std::chrono::duration<double>>::Error(
            TimeError::kUninitialized);
    }
    double day_diff = static_cast<double>(tai_.mjd.day - other.tai_.mjd.day);
    double sec_diff =
        (day_diff + tai_.mjd.frac_day - other.tai_.mjd.frac_day) * kSecPerDay;
    return TimeResult<std::chrono::duration<double>>::Ok(
        std::chrono::duration<double>(sec_diff));
}

TimeSys& TimeSys::AddSecondsInPlace(double seconds) {
    if (!initialized_) {
        status_      = TimeStatus::kInvalid;
        initialized_ = false;
        return *this;
    }
    double  tai_seconds = tai_.mjd.frac_day * kSecPerDay + seconds;
    MjdTime mjd         = NormalizeMjdSeconds(tai_.mjd.day, tai_seconds);
    tai_.mjd            = mjd;
    status_             = TimeStatus::kValid;
    return *this;
}

TimeResult<LeapSecondTable> LeapSecondTable::LoadFromCsv(
    const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        return TimeResult<LeapSecondTable>::Error(TimeError::kOutOfRange);
    }
    std::vector<LeapSecondEntry> entries;
    std::string                  line;
    while (std::getline(in, line)) {
        if (line.empty()) { continue; }
        if (line[0] == '#') { continue; }
        std::stringstream        ss(line);
        std::string              token;
        std::vector<std::string> cols;
        while (std::getline(ss, token, ',')) { cols.push_back(token); }
        if (cols.size() < 4) { continue; }
        LeapSecondEntry entry{};
        entry.year          = std::stoi(cols[0]);
        entry.month         = std::stoi(cols[1]);
        entry.day           = std::stoi(cols[2]);
        entry.tai_minus_utc = std::stoi(cols[3]);
        entries.push_back(entry);
    }
    return TimeResult<LeapSecondTable>::Ok(
        LeapSecondTable::FromEntries(entries));
}

LeapSecondTable LeapSecondTable::FromEntries(
    const std::vector<LeapSecondEntry>& entries) {
    LeapSecondTable table{};
    table.entries_ = entries;
    std::sort(table.entries_.begin(), table.entries_.end(),
              [](const LeapSecondEntry& a, const LeapSecondEntry& b) {
                  if (a.year != b.year) { return a.year < b.year; }
                  if (a.month != b.month) { return a.month < b.month; }
                  return a.day < b.day;
              });
    return table;
}

bool LeapSecondTable::IsValid() const { return !entries_.empty(); }

TimeResult<int> LeapSecondTable::GetTaiMinusUtcSeconds(
    const CivilTime& utc) const {
    if (!IsCivilTimeValid(utc)) {
        return TimeResult<int>::Error(TimeError::kInvalidCivilTime);
    }
    if (!IsValid()) {
        return TimeResult<int>::Error(TimeError::kMissingLeapSeconds);
    }
    TimeResult<int64_t> utc_day =
        MjdDayFromCivilDate(utc.year, utc.month, utc.day);
    if (!utc_day.ok()) { return TimeResult<int>::Error(utc_day.error); }
    if (utc.sec >= 60.0) {
        bool is_leaping         = false;
        int  leap_tai_minus_utc = 0;
        for (const auto& entry : entries_) {
            TimeResult<int64_t> entry_day =
                MjdDayFromCivilDate(entry.year, entry.month, entry.day);
            if (!entry_day.ok()) { continue; }
            if (utc_day.value + 1 == entry_day.value) {
                is_leaping         = true;
                leap_tai_minus_utc = entry.tai_minus_utc;
                break;
            }
        }
        if (is_leaping) { return TimeResult<int>::Ok(leap_tai_minus_utc); }
        return TimeResult<int>::Error(TimeError::kInvalidCivilTime);
    }

    int  tai_minus_utc = entries_.front().tai_minus_utc;
    bool found         = false;
    for (const auto& entry : entries_) {
        TimeResult<int64_t> entry_day =
            MjdDayFromCivilDate(entry.year, entry.month, entry.day);
        if (!entry_day.ok()) { continue; }
        if (utc_day.value >= entry_day.value) {
            tai_minus_utc = entry.tai_minus_utc;
            found         = true;
        }
    }
    if (!found) { return TimeResult<int>::Error(TimeError::kOutOfRange); }
    return TimeResult<int>::Ok(tai_minus_utc);
}

TimeResult<int> LeapSecondTable::GetTaiMinusUtcSeconds(
    const UtcMjd& utc) const {
    if (!IsValid()) {
        return TimeResult<int>::Error(TimeError::kMissingLeapSeconds);
    }
    if (utc.mjd.frac_day < 0.0 || utc.mjd.frac_day >= 1.0 ||
        !std::isfinite(utc.mjd.frac_day)) {
        return TimeResult<int>::Error(TimeError::kInvalidMjd);
    }
    TimeResult<CivilTime> civil =
        CivilFromMjdDay(utc.mjd.day, utc.mjd.frac_day * kSecPerDay);
    if (!civil.ok()) { return TimeResult<int>::Error(civil.error); }
    return GetTaiMinusUtcSeconds(civil.value);
}

TimeResult<CivilTime> LeapSecondTable::TaiToUtcCivil(const TaiMjd& tai) const {
    if (!IsValid()) {
        return TimeResult<CivilTime>::Error(TimeError::kMissingLeapSeconds);
    }
    if (tai.mjd.frac_day < 0.0 || tai.mjd.frac_day >= 1.0 ||
        !std::isfinite(tai.mjd.frac_day)) {
        return TimeResult<CivilTime>::Error(TimeError::kInvalidMjd);
    }
    double tai_seconds = static_cast<double>(tai.mjd.day) * kSecPerDay +
                         tai.mjd.frac_day * kSecPerDay;
    if (entries_.empty()) {
        return TimeResult<CivilTime>::Error(TimeError::kMissingLeapSeconds);
    }

    for (const auto& entry : entries_) {
        TimeResult<int64_t> entry_day =
            MjdDayFromCivilDate(entry.year, entry.month, entry.day);
        if (!entry_day.ok()) { continue; }
        double tai_effective =
            static_cast<double>(entry_day.value) * kSecPerDay +
            static_cast<double>(entry.tai_minus_utc);
        if (tai_seconds >= tai_effective - 1.0 && tai_seconds < tai_effective) {
            TimeResult<CivilTime> date =
                CivilFromMjdDay(entry_day.value - 1, 0.0);
            if (!date.ok()) { return TimeResult<CivilTime>::Error(date.error); }
            double    leap_frac = tai_seconds - (tai_effective - 1.0);
            CivilTime result    = date.value;
            result.hour         = 23;
            result.min          = 59;
            result.sec          = 60.0 + leap_frac;
            return TimeResult<CivilTime>::Ok(result);
        }
    }

    int  best_tai_minus_utc = entries_.front().tai_minus_utc;
    bool found              = false;
    for (const auto& entry : entries_) {
        TimeResult<int64_t> entry_day =
            MjdDayFromCivilDate(entry.year, entry.month, entry.day);
        if (!entry_day.ok()) { continue; }
        double tai_effective =
            static_cast<double>(entry_day.value) * kSecPerDay +
            static_cast<double>(entry.tai_minus_utc);
        if (tai_seconds >= tai_effective) {
            best_tai_minus_utc = entry.tai_minus_utc;
            found              = true;
        }
    }
    if (!found) { return TimeResult<CivilTime>::Error(TimeError::kOutOfRange); }
    double  utc_seconds = tai_seconds - static_cast<double>(best_tai_minus_utc);
    int64_t utc_day =
        static_cast<int64_t>(std::floor(utc_seconds / kSecPerDay));
    double seconds_of_day =
        utc_seconds - static_cast<double>(utc_day) * kSecPerDay;
    if (seconds_of_day < 0.0) {
        utc_day -= 1;
        seconds_of_day += kSecPerDay;
    }
    return CivilFromMjdDay(utc_day, seconds_of_day);
}

/// \cond DOXYGEN_SKIP
template <>
TimeError TimeSys::Set<CivilTime>(const CivilTime& t) {
    return SetUtcCivil(t);
}

template <>
TimeError TimeSys::Set<UtcMjd>(const UtcMjd& t) {
    return SetUtcMjd(t);
}

template <>
TimeError TimeSys::Set<Ut1Mjd>(const Ut1Mjd& t) {
    if (!IsMjdValid(t.mjd)) {
        status_ = TimeStatus::kInvalid;
        return TimeError::kInvalidMjd;
    }
    TimeError ready = EnsureReadyForUt1();
    if (ready != TimeError::kOk) {
        status_ = TimeStatus::kInvalid;
        return ready;
    }
    double  utc_seconds = t.mjd.frac_day * kSecPerDay - ut1_minus_utc_seconds_;
    MjdTime utc_mjd     = NormalizeMjdSeconds(t.mjd.day, utc_seconds);
    UtcMjd  utc{utc_mjd};
    TimeResult<int> tai_minus_utc = leap_seconds_.GetTaiMinusUtcSeconds(utc);
    if (!tai_minus_utc.ok()) {
        status_ = TimeStatus::kInvalid;
        return tai_minus_utc.error;
    }
    double tai_seconds = utc_mjd.frac_day * kSecPerDay +
                         static_cast<double>(tai_minus_utc.value);
    tai_         = TaiMjd{NormalizeMjdSeconds(utc_mjd.day, tai_seconds)};
    initialized_ = true;
    status_      = TimeStatus::kValid;
    return TimeError::kOk;
}

template <>
TimeError TimeSys::Set<TaiMjd>(const TaiMjd& t) {
    return SetTaiMjd(t);
}

template <>
TimeError TimeSys::Set<TtMjd>(const TtMjd& t) {
    return SetTtMjd(t);
}

template <>
TimeError TimeSys::Set<GpstTime>(const GpstTime& t) {
    return SetGpst(t);
}

template <>
TimeError TimeSys::Set<BdtTime>(const BdtTime& t) {
    return SetBdt(t);
}

template <>
TimeResult<CivilTime> TimeSys::Get<CivilTime>() const {
    return GetUtcCivil();
}

template <>
TimeResult<UtcMjd> TimeSys::Get<UtcMjd>() const {
    return GetUtcMjd();
}

template <>
TimeResult<Ut1Mjd> TimeSys::Get<Ut1Mjd>() const {
    return GetUt1Mjd();
}

template <>
TimeResult<TaiMjd> TimeSys::Get<TaiMjd>() const {
    return GetTaiMjd();
}

template <>
TimeResult<TtMjd> TimeSys::Get<TtMjd>() const {
    return GetTtMjd();
}

template <>
TimeResult<GpstTime> TimeSys::Get<GpstTime>() const {
    return GetGpst();
}

template <>
TimeResult<BdtTime> TimeSys::Get<BdtTime>() const {
    return GetBdt();
}
/// \endcond

}  // namespace unit::time
