package com.kneesense.repository;

import com.kneesense.domain.Report;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ReportRepository extends JpaRepository<Report, Long> {

    Optional<Report> findByResult_Id(Long resultId);

    Optional<Report> findByResult_IdAndResult_Upload_User_Id(Long resultId, Long userId);
}
