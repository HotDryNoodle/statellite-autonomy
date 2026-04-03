#include "orbit_time.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

std::map<std::string, std::string> ParseArgs(int argc, char* argv[]) {
    std::map<std::string, std::string> parsed;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg.rfind("--", 0) != 0 || i + 1 >= argc) { continue; }
        parsed[arg.substr(2)] = argv[++i];
    }
    return parsed;
}

std::string EscapeJson(const std::string& text) {
    std::string escaped;
    for (char ch : text) {
        if (ch == '"' || ch == '\\') { escaped.push_back('\\'); }
        escaped.push_back(ch);
    }
    return escaped;
}

double MjdDiffSeconds(const unit::time::MjdTime& a,
                      const unit::time::MjdTime& b) {
    const int day_diff = static_cast<int>(a.day - b.day);
    const double frac_diff = a.frac_day - b.frac_day;
    return static_cast<double>(day_diff) * unit::time::kSecPerDay +
           frac_diff * unit::time::kSecPerDay;
}

unit::time::TimeResult<unit::time::LeapSecondTable> LoadLeapSeconds(
    const std::string& path) {
    return unit::time::LeapSecondTable::LoadFromCsv(path);
}

unit::time::CivilTime ReadCivil(const std::map<std::string, std::string>& args) {
    return unit::time::CivilTime{
        std::stoi(args.at("year")),
        std::stoi(args.at("month")),
        std::stoi(args.at("day")),
        std::stoi(args.at("hour")),
        std::stoi(args.at("minute")),
        std::stod(args.at("second")),
    };
}

void PrintJson(
    const std::string& scenario_id,
    const std::vector<std::pair<std::string, std::string>>& fields) {
    std::cout << "{";
    std::cout << "\"scenario_id\":\"" << EscapeJson(scenario_id) << "\"";
    for (const auto& field : fields) {
        std::cout << ",\"" << EscapeJson(field.first) << "\":" << field.second;
    }
    std::cout << "}\n";
}

int RunRoundtrip(const std::map<std::string, std::string>& args) {
    auto leap_seconds = LoadLeapSeconds(args.at("leap-file"));
    if (!leap_seconds.ok()) { return 1; }

    const auto civil = ReadCivil(args);
    const int iterations = std::stoi(args.at("iterations"));
    double max_tt_error = 0.0;
    double max_gpst_error = 0.0;

    const auto started = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        unit::time::TimeSys time;
        time.SetLeapSecondTable(leap_seconds.value);
        if (time.Set(civil) != unit::time::TimeError::kOk) { return 1; }

        const auto tt = time.Get<unit::time::TtMjd>();
        const auto utc = time.Get<unit::time::UtcMjd>();
        const auto gpst = time.Get<unit::time::GpstTime>();
        if (!tt.ok() || !utc.ok() || !gpst.ok()) { return 1; }

        unit::time::TimeSys from_tt;
        from_tt.SetLeapSecondTable(leap_seconds.value);
        if (from_tt.Set(tt.value) != unit::time::TimeError::kOk) { return 1; }
        const auto utc_from_tt = from_tt.Get<unit::time::UtcMjd>();
        if (!utc_from_tt.ok()) { return 1; }

        unit::time::TimeSys from_gpst;
        from_gpst.SetLeapSecondTable(leap_seconds.value);
        if (from_gpst.Set(gpst.value) != unit::time::TimeError::kOk) { return 1; }
        const auto utc_from_gpst = from_gpst.Get<unit::time::UtcMjd>();
        if (!utc_from_gpst.ok()) { return 1; }

        max_tt_error = std::max(
            max_tt_error,
            std::fabs(MjdDiffSeconds(utc_from_tt.value.mjd, utc.value.mjd)));
        max_gpst_error = std::max(
            max_gpst_error,
            std::fabs(MjdDiffSeconds(utc_from_gpst.value.mjd, utc.value.mjd)));
    }
    const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
        Clock::now() - started);

    std::ostringstream per_iteration;
    per_iteration << std::fixed << std::setprecision(6)
                  << static_cast<double>(elapsed.count()) /
                         static_cast<double>(iterations);
    std::ostringstream tt_error;
    tt_error << std::setprecision(16) << max_tt_error;
    std::ostringstream gpst_error;
    gpst_error << std::setprecision(16) << max_gpst_error;

    PrintJson("time_roundtrip_utc_tt_gpst",
              {
                  {"elapsed_ns_per_iteration", per_iteration.str()},
                  {"max_tt_roundtrip_error_sec", tt_error.str()},
                  {"max_gpst_roundtrip_error_sec", gpst_error.str()},
              });
    return 0;
}

int RunLeapSecondBoundary(const std::map<std::string, std::string>& args) {
    auto leap_seconds = LoadLeapSeconds(args.at("leap-file"));
    if (!leap_seconds.ok()) { return 1; }
    const int iterations = std::stoi(args.at("iterations"));

    double dt1_error = 0.0;
    double dt2_error = 0.0;
    double dt3_error = 0.0;

    const auto started = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        unit::time::TimeSys time1;
        time1.SetLeapSecondTable(leap_seconds.value);
        if (time1.Set(unit::time::CivilTime{2015, 6, 30, 23, 59, 59.0}) !=
            unit::time::TimeError::kOk) {
            return 1;
        }
        const auto tai1 = time1.Get<unit::time::TaiMjd>();
        if (!tai1.ok()) { return 1; }

        unit::time::TimeSys time2;
        time2.SetLeapSecondTable(leap_seconds.value);
        if (time2.Set(unit::time::CivilTime{2015, 6, 30, 23, 59, 60.0}) !=
            unit::time::TimeError::kOk) {
            return 1;
        }
        const auto tai2 = time2.Get<unit::time::TaiMjd>();
        if (!tai2.ok()) { return 1; }

        unit::time::TimeSys time3;
        time3.SetLeapSecondTable(leap_seconds.value);
        if (time3.Set(unit::time::CivilTime{2015, 7, 1, 0, 0, 0.0}) !=
            unit::time::TimeError::kOk) {
            return 1;
        }
        const auto tai3 = time3.Get<unit::time::TaiMjd>();
        if (!tai3.ok()) { return 1; }

        dt1_error = std::max(
            dt1_error,
            std::fabs(MjdDiffSeconds(tai2.value.mjd, tai1.value.mjd) - 2.0));
        dt2_error = std::max(
            dt2_error,
            std::fabs(MjdDiffSeconds(tai3.value.mjd, tai1.value.mjd) - 2.0));
        dt3_error = std::max(
            dt3_error,
            std::fabs(MjdDiffSeconds(tai3.value.mjd, tai2.value.mjd)));
    }
    const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
        Clock::now() - started);

    std::ostringstream per_iteration;
    per_iteration << std::fixed << std::setprecision(6)
                  << static_cast<double>(elapsed.count()) /
                         static_cast<double>(iterations);
    std::ostringstream err1;
    err1 << std::setprecision(16) << dt1_error;
    std::ostringstream err2;
    err2 << std::setprecision(16) << dt2_error;
    std::ostringstream err3;
    err3 << std::setprecision(16) << dt3_error;

    PrintJson("time_leap_second_boundary_2015",
              {
                  {"elapsed_ns_per_iteration", per_iteration.str()},
                  {"dt_1_sec_error", err1.str()},
                  {"dt_2_sec_error", err2.str()},
                  {"dt_3_sec_error", err3.str()},
              });
    return 0;
}

int RunUt1Dependency(const std::map<std::string, std::string>& args) {
    auto leap_seconds = LoadLeapSeconds(args.at("leap-file"));
    if (!leap_seconds.ok()) { return 1; }
    const auto civil = ReadCivil(args);
    const int iterations = std::stoi(args.at("iterations"));
    const double target_offset = std::stod(args.at("ut1-minus-utc"));

    bool missing_ut1_detected = true;
    bool ut1_available_after_set = true;
    double max_error = 0.0;

    const auto started = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        unit::time::TimeSys time;
        time.SetLeapSecondTable(leap_seconds.value);
        if (time.Set(civil) != unit::time::TimeError::kOk) { return 1; }

        const auto ut1_before = time.Get<unit::time::Ut1Mjd>();
        missing_ut1_detected = missing_ut1_detected &&
                               (!ut1_before.ok() &&
                                ut1_before.error ==
                                    unit::time::TimeError::kMissingUt1Utc);

        time.SetUt1MinusUtcSeconds(target_offset);
        const auto ut1_after = time.Get<unit::time::Ut1Mjd>();
        const auto utc = time.Get<unit::time::UtcMjd>();
        if (!ut1_after.ok() || !utc.ok()) {
            ut1_available_after_set = false;
            continue;
        }
        max_error = std::max(
            max_error,
            std::fabs(MjdDiffSeconds(ut1_after.value.mjd, utc.value.mjd) -
                      target_offset));
    }
    const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
        Clock::now() - started);

    std::ostringstream per_iteration;
    per_iteration << std::fixed << std::setprecision(6)
                  << static_cast<double>(elapsed.count()) /
                         static_cast<double>(iterations);
    std::ostringstream error;
    error << std::setprecision(16) << max_error;

    PrintJson("time_ut1_dependency",
              {
                  {"elapsed_ns_per_iteration", per_iteration.str()},
                  {"ut1_offset_error_sec", error.str()},
                  {"missing_ut1_detected",
                   missing_ut1_detected ? "true" : "false"},
                  {"ut1_available_after_set",
                   ut1_available_after_set ? "true" : "false"},
              });
    return 0;
}

int RunInvalidInputs(const std::map<std::string, std::string>& args) {
    const int iterations = std::stoi(args.at("iterations"));
    bool invalid_civil_rejected = true;
    bool invalid_gpst_rejected = true;

    const auto started = Clock::now();
    for (int i = 0; i < iterations; ++i) {
        unit::time::TimeSys time;
        invalid_civil_rejected =
            invalid_civil_rejected &&
            time.Set(unit::time::CivilTime{2015, 7, 2, 23, 59, 61.0}) ==
                unit::time::TimeError::kInvalidCivilTime;
        invalid_gpst_rejected =
            invalid_gpst_rejected &&
            time.Set(unit::time::GpstTime{1, unit::time::kSecPerWeek + 1.0}) ==
                unit::time::TimeError::kInvalidWeekSeconds;
    }
    const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
        Clock::now() - started);

    std::ostringstream per_iteration;
    per_iteration << std::fixed << std::setprecision(6)
                  << static_cast<double>(elapsed.count()) /
                         static_cast<double>(iterations);

    PrintJson("time_invalid_inputs",
              {
                  {"elapsed_ns_per_iteration", per_iteration.str()},
                  {"invalid_civil_rejected",
                   invalid_civil_rejected ? "true" : "false"},
                  {"invalid_gpst_rejected",
                   invalid_gpst_rejected ? "true" : "false"},
              });
    return 0;
}

}  // namespace

int main(int argc, char* argv[]) {
    const auto args = ParseArgs(argc, argv);
    const auto kind = args.find("kind");
    if (kind == args.end()) {
        std::cerr << "missing --kind\n";
        return 1;
    }

    if (kind->second == "roundtrip") { return RunRoundtrip(args); }
    if (kind->second == "leap_second_boundary") {
        return RunLeapSecondBoundary(args);
    }
    if (kind->second == "ut1_dependency") { return RunUt1Dependency(args); }
    if (kind->second == "invalid_inputs") { return RunInvalidInputs(args); }

    std::cerr << "unsupported kind: " << kind->second << "\n";
    return 1;
}
