package com.handy.ocr.util;

import com.handy.ocr.vo.accurategeneral.AccurateGeneralVo;
import lombok.val;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPageSz;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTSectPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STPageOrientation;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.math.BigInteger;

/**
 * @author hs
 * @Description: {使用poi生成word}
 * @date 2019/9/10 10:17
 */
public class PoiToWord {
    public static final int HORIZONTAL_OFFSET = 1764;
    public static final int HEAD_OFFSET = 1397;
    public static final int FIX_MULTIPLE = 20;

    /**
     * poi生成word
     *
     * @param accurateGeneralVo
     * @throws Exception
     */
    public static void poiToWord(AccurateGeneralVo accurateGeneralVo, String url) throws Exception {
        // 获取图片宽度
        File picture = new File(url);
        BufferedImage sourceImg = ImageIO.read(new FileInputStream(picture));
        float imgWidth = sourceImg.getWidth();
        float imgHeight = sourceImg.getHeight();

        XWPFDocument document = new XWPFDocument();
        CTSectPr sectPr = document.getDocument().getBody().addNewSectPr();
        CTPageSz pgSz = sectPr.addNewPgSz();
        val words_result = accurateGeneralVo.getWords_result();


        System.out.println("imgWidth:" + imgWidth + "---imgHeight----" + imgHeight);

        pgSz.setW(BigInteger.valueOf(Float.valueOf((imgWidth * FIX_MULTIPLE + 200) + "").longValue()));
        pgSz.setH(BigInteger.valueOf(Float.valueOf((imgHeight * FIX_MULTIPLE + HEAD_OFFSET) + "").longValue()));
        pgSz.setOrient(STPageOrientation.LANDSCAPE);
        FileOutputStream out = new FileOutputStream(new File(url + ".docx"));


        for (int i = 0; i < words_result.size(); i++) {
            String words = words_result.get(i).getWords();
            val location = words_result.get(i).getLocation();

            val vertexes_location = words_result.get(i).getVertexes_location();
            float top = vertexes_location.get(0).getY();
            if (i != 0) {
                val vertexes_location1 = words_result.get(i - 1).getVertexes_location();
                int y = vertexes_location1.get(3).getY();
                top = top - y;
            }
            //段落
            XWPFParagraph firstParagraph = document.createParagraph();

            float a = top / imgHeight * imgHeight;
            // 设置段落的前后间距
            float b = location.getLeft() / imgWidth * imgWidth;
            // 设置段落的左缩进
            System.out.println("top:" + a + "---getLeft----" + b);
            int leftWithMargin = (int) Math.abs(b) * FIX_MULTIPLE;
            firstParagraph.setIndentationLeft(leftWithMargin - HORIZONTAL_OFFSET);
            //  firstParagraph.setIndentationRight(-200);

            if (i == 0) {
                int firstTopWithHead = (int) Math.abs(top) * FIX_MULTIPLE;
                int firstTop = firstTopWithHead > HEAD_OFFSET ? firstTopWithHead - HEAD_OFFSET : 0;
                firstParagraph.setSpacingBefore(firstTop);
            } else {
                firstParagraph.setSpacingBefore((int) (Math.abs(a) * FIX_MULTIPLE));
            }

            XWPFRun run = firstParagraph.createRun();
            run.setText(words);
            run.setFontSize(location.getHeight() * 3 / 4);
        }
        document.write(out);
        out.close();
    }
}
