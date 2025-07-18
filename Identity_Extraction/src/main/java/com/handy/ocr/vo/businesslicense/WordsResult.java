package com.handy.ocr.vo.businesslicense;

import com.handy.ocr.vo.Words;
import lombok.Data;

import java.io.Serializable;

/**
 * @author hanshuai
 * @Description: {营业职照识别结果}
 * @date 2019/9/10
 */
@Data
public class WordsResult  implements Serializable {
    /**
     * 社会信用代码
     */
    private Words socialCreditCode;
    /**
     * 组成形式
     */
    private Words composingForm;
    /**
     * 经营范围
     */
    private Words businessScope;
    /**
     * 法人
     */
    private Words legalPerson;
    /**
     * 成立日期
     */
    private Words establishmentDate;
    /**
     * 注册资本
     */
    private Words registeredCapital;
    /**
     * 证件编号
     */
    private Words certificateNumber;
    /**
     * 地址
     */
    private Words site;
    /**
     * 单位名称
     */
    private Words organizationName;
    /**
     * 类型
     */
    private Words type;
    /**
     * 有效期
     */
    private Words validityPeriod;
}