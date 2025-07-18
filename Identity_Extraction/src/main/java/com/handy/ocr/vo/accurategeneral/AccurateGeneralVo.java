package com.handy.ocr.vo.accurategeneral;

import lombok.Data;

import java.io.Serializable;
import java.util.List;

/**
 * @author hanshuai
 * @Description: {通用文字识别(含位置高精度版本)}
 * @date 2019/9/10
 */
@Data
public class AccurateGeneralVo implements Serializable {
    /**
     * 唯一的log id，用于问题定位
     */
    private long log_id;
    /**
     * 定位和识别结果数组
     */
    private List<WordsResult> words_result;
    /**
     * 识别结果数，表示words_result的元素个数
     */
    private int words_result_num;
    /**
     * 图像方向，当detect_direction=true时存在。
     * - -1:未定义，
     * - 0:正向，
     * - 1: 逆时针90度，
     * - 2:逆时针180度，
     * - 3:逆时针270度
     */
    private int direction;
}
