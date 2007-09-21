function getCorrelation(thickness_L6b, thickness_L6a, thickness_L5, thickness_L4, thickness_L2and3, thickness_L1) 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% returns an image showing the correaltion between the layer thicknesses
% returns a second image showing the Spearman Correlation
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

data= [thickness_L1; thickness_L2and3; thickness_L4; thickness_L5; thickness_L6a; thickness_L6b];

i=6;
d=[];
%computes the cumulative height
while i~=0
    d(i,:)= data (i,:);
    if (i~=6)
        d(i,:)=d(i,:)+d(i+1,:);
    end
    i=i-1;
end

data (7,:)= d(1,:); %store total height in data(7,:)


figure
imagesc(corrcoef(data'))

% axis xy;
 a = gca;
 set(a, 'YTickLabel', {'Layer1' ,'Layer2-3', 'Layer4', 'Layer5', 'Layer6a','Layer6b', 'Total Height'}); 
 set(a, 'XTickLabel', {'Layer1' ,'Layer2-3', 'Layer4', 'Layer5', 'Layer6a','Layer6b', 'Total Height'});
 title ('Correlations between layer thicknesses')
 colorbar
 caxis([-1 1])
 print(gcf, '-dpng', '~/Correlation.png')
 
 figure
 imagesc(corr(data','type','spearman'))
 
 a = gca;
 set(a, 'YTickLabel', {'Layer1' ,'Layer2-3', 'Layer4', 'Layer5', 'Layer6a','Layer6b', 'Total Height'}); 
 set(a, 'XTickLabel', {'Layer1' ,'Layer2-3', 'Layer4', 'Layer5', 'Layer6a','Layer6b', 'Total Height'});
 title ('Rank Correlations between layer thicknesses')
 colorbar 
 caxis([-1 1])
 print(gcf, '-dpng', '~/Spearman.png')