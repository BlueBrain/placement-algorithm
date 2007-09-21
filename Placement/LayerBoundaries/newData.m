function newData
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%provides four plots: plot 1: plot of layer boundaries (given by Sonia and 
%                             Rodrigo on September 6 2007)
%                     plot 2: same plot with layer boundaries interpolated,
%                             and with additional lines showing the
%                             orientation that needs to be taken to 
%                             calculate layer thicknesses
%                     plot 3: shows correlation between layer thicknesses, 
%                             and the correlation with the total height
%                     plot 4: Spearman correlation
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%reading data from excel files
Layer6a= xlsread('L6a.xls');
Layer6b= xlsread('L6b.xls');
Layer5= xlsread('L5.xls');
Layer4= xlsread('L4.xls');
Layer2and3= xlsread('L2.xls');
Layer1 = xlsread('L1.xls');
bottom= xlsread('bottom.xls');

%plotting Layer Boundaries
figure 
hold on

plot (Layer1(:,1), Layer1(:,2),'r')
plot(Layer2and3(:,1), Layer2and3(:,2),'c')
plot(Layer4(:,1), Layer4(:,2),'m')
plot(Layer5(:,1), Layer5(:,2),'k')
plot (Layer6a(:,1), Layer6a(:,2),'b')
plot (Layer6b(:,1), Layer6b(:,2),'g')
plot (bottom(:,1), bottom(:,2),'g')
axis ('ij')
axis([3873 10046 0 4000])
title ('Layer boundaries')
hold off


figure 
hold on
%computing step size between lines 
Array= [diff(Layer1(:,1));diff(Layer2and3(:,1));diff(Layer4(:,1));diff(Layer5(:,1));diff(Layer6a(:,1));diff(Layer6b(:,1));diff(bottom(:,1))];
m = mean (Array);
m= m/2;

 xi= [3873:m:10046];  

 %plotting Layer Boundaries interpolated
 yi= interp1 (Layer1(:,1),Layer1(:,2) , xi, 'cubic');
 plot (xi,yi,'r')
 
 yi= interp1 (Layer2and3(:,1),Layer2and3(:,2) , xi, 'cubic');
 plot (xi,yi,'c')
 
 yi= interp1 (Layer4(:,1),Layer4(:,2) , xi, 'cubic');
 plot (xi,yi,'m')
 
 yi= interp1 (Layer5(:,1),Layer5(:,2) , xi, 'cubic');
 plot (xi,yi,'k')
 
 yi= interp1 (Layer6a(:,1),Layer6a(:,2) , xi, 'cubic');
 plot (xi,yi,'b')
 
 yi= interp1 (Layer6b(:,1),Layer6b(:,2) , xi, 'cubic');
 plot (xi,yi,'g') 
 
 yi= interp1 (bottom(:,1),bottom(:,2) , xi, 'cubic');
 plot (xi,yi,'g')
 
 axis([3873 10046 0 4000])
axis('ij')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%ADDED
%fitting the bottom line
fit = polyfit(bottom(:,1),bottom(:,2) ,1);
coeffCorrected = polyval(fit,bottom(:,1));
plot(bottom(:,1),coeffCorrected,'k-')

%fitting upper boundary of Layer1
fit2 = polyfit(Layer1(:,1),Layer1(:,2) ,1);
coeffCorrected2 = polyval(fit2,Layer1(:,1));
plot(Layer1(:,1),coeffCorrected2,'k-')

%obtain slope of orthogonal lines
mOrth= orthogonalLine (fit, fit2);
points= [3873:10*m:10046];
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
 

  Lower = interp1(bottom(:,1),bottom(:,2),xi ,'cubic');
  
 
 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
 %ADDED
 %obtain equation of orthogonal lines and plot them
 g= 3500:100:10000;
 %choose points along which the lines cut the bottom line
 for j = 1: length(points)
  
  if j==1
      x= xi(j);
      y=Lower(j);
      
  else
      x= xi(10*(j-1));
      y= Lower(10*(j-1));
      
  end
  b(j)= y - mOrth * x;
  lineEQ= mOrth*g+b(j);
  plot (g,lineEQ)
  
 end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
 

%obtain Layer thicknesses
[thickness_L6b, thickness_L6a, thickness_L5, thickness_L4, thickness_L2and3, thickness_L1] = getThickness (Layer1,Layer2and3,Layer4,Layer5,Layer6a,Layer6b,bottom, m, mOrth,b);

 
 
%chooseLayerBoundaries (m,L1,L2and3,L4,L5,L6a,L6b,bottom);
title ('Layer boundaries interpolated')
print(gcf, '-dpng', '~/LayerBoundaries.png')
hold off
 
%obtain Correlation plots
getCorrelation(thickness_L6b, thickness_L6a, thickness_L5, thickness_L4, thickness_L2and3, thickness_L1);
 
 
 

