package com.handy.ocr.vo.idcardfront;

import com.handy.ocr.vo.Words;
import lombok.Data;

import java.io.Serializable;

/**
 * @author hanshuai
 * @Description: {身份证正面识别结果}
 * @date 2019/9/10
 */
@Data
public class WordsResult implements Serializable {

    /**
     * 姓名
     */
    private Words name;
    /**
     * 民族
     */
    private Words nation;
    /**
     * 住址
     */
    private Words address;
    /**
     * 公民身份号码
     */
    private Words citizenIdNumber;
    /**
     * 出生
     */
    private Words birth;
    /**
     * 性别
     */
    private Words sex;
}